#!/usr/bin/env python3
"""PreToolUse hook: fences a build session off from live data, docker and forced pushes.

Reads the tool call as JSON on stdin. Exit 0 lets it through, exit 2 refuses it and
hands stderr to the agent. A fence against mistakes, not against an attacker.
"""

import json
import os
import re
import shlex
import sys

TAIL = (
    "Do not work around the fence. If the task cannot go on without this, "
    "stop and end your report with:\nBLOCKED: <short reason>"
)
ADMIN = (
    "--admin skips branch protection",
    "Merge with `gh pr merge <n> --squash --auto --delete-branch` and let the checks pass.",
)
NO_VERIFY = (
    "--no-verify (`git commit -n`) skips the commit hooks",
    "Fix what the hook reports, then commit or push again.",
)
FORCE = (
    "a force push rewrites the remote branch",
    "Add new commits and push them with a plain `git push`.",
)
SETTINGS = (
    "repo:apply-settings changes the GitHub repo settings and branch protection",
    "`mise run repo:check-settings` only reads them.",
)
DOCKER = (
    "the docker subcommand `{}` starts, stops or removes containers and volumes on the live host",
    "Reading is fine (docker ps, logs, inspect). `mise run test:webkit` runs its own container.",
)
LIVE = (
    "{} writes under the live folder {}",
    "Read it only: ls, cat, cp to another folder, `sqlite3 -readonly`, or a "
    "`file:...?mode=ro` URI. Keep test data in a temp folder.",
)

HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_]\w*)\1")
LIVE_NAME = re.compile(r"\.local/share/blattwerk(?![\w-])")
SCRIPTERS = re.compile(r"python[\d.]*|node|perl|ruby")
PREFIXES = {"sudo", "env", "time", "nohup", "nice", "command", "exec", "xargs"}
PREFIXES |= {"{", "}", "!", "if", "then", "else", "elif", "do", "while", "until"}
PREFIX_VALUE_OPTS = {"-n", "-I", "-P", "-L", "-d", "-u", "-g", "--with"}
DOCKER_VALUE_OPTS = {"-f", "--file", "-p", "--project-name", "--project-directory", "--env-file"}
DOCKER_VALUE_OPTS |= {"--profile", "--context", "-H", "--host", "-c", "--config", "-l"}
DOCKER_VALUE_OPTS |= {"--log-level"}
DOCKER_GROUPS = {"compose", "container", "image", "network", "builder", "buildx"}
DOCKER_BAD = {"up", "down", "rm", "stop", "kill", "system", "volume"}
WRITE_ANY = {"rm", "rmdir", "unlink", "shred", "truncate", "touch", "mkdir", "chmod", "chown"}
WRITE_ANY |= {"tee", "mv"}
WRITE_LAST = {"cp", "rsync", "install", "ln"}


class Refused(Exception):
    def __init__(self, rule: tuple[str, str], *names: str) -> None:
        super().__init__(rule[0].format(*names))
        self.todo = rule[1]


def live_dir() -> str:
    return os.path.realpath(os.path.join(os.environ["HOME"], ".local/share/blattwerk"))


def resolve(path: str, cwd: str) -> str:
    path = re.split(r"[*?\[]", path)[0]  # a glob counts as the folder it starts in
    path = os.path.expanduser(os.path.expandvars(path))
    return os.path.realpath(os.path.join(cwd, path))


def guard(path: str, cwd: str, what: str, parents: bool = False) -> None:
    """Refuse when path lies under the live folder (or, for rm and mv, holds it)."""
    live, full = live_dir(), resolve(path, cwd)
    holds = parents and (live + os.sep).startswith(full.rstrip(os.sep) + os.sep)
    if (full + os.sep).startswith(live + os.sep) or holds:
        raise Refused(LIVE, what, live)


def guard_script(text: str, what: str) -> None:
    if LIVE_NAME.search(text) and "mode=ro" not in text:
        raise Refused(LIVE, what + " that names the live folder without mode=ro", live_dir())


def strip_heredocs(text: str, bodies: list[str]) -> str:
    """Move each heredoc body into bodies and leave `<< __HD<n>__` in its place."""

    def mark(_match: re.Match[str]) -> str:
        bodies.append("")
        return f"<< __HD{len(bodies) - 1}__ "

    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        delims = [m.group(2) for m in HEREDOC.finditer(lines[i])]
        first = len(bodies)
        out.append(HEREDOC.sub(mark, lines[i]))
        i += 1
        for n, delim in enumerate(delims, first):
            start = i
            while i < len(lines) and not re.fullmatch(rf"\s*{delim}\s*(\).*)?", lines[i]):
                i += 1
            bodies[n] = "\n".join(lines[start:i])
            if i < len(lines):
                out.append(lines[i].strip()[len(delim) :])
                i += 1
    return "\n".join(out)


def close_paren(text: str, i: int) -> int:
    depth, quote = 1, ""
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 1
        elif quote:
            quote = "" if c == quote else quote
        elif c in "'\"":
            quote = c
        elif c in "()":
            depth += 1 if c == "(" else -1
            if depth == 0:
                return i
        i += 1
    return i


def lift_subs(text: str) -> tuple[str, list[str]]:
    """Cut $(...) and `...` out of text, drop comments, turn unquoted newlines into `;`."""
    out, subs, quote, i = [], [], "", 0
    while i < len(text):
        c = text[i]
        if c == "\\" and quote != "'":
            out.append("" if text[i + 1 : i + 2] == "\n" else text[i : i + 2])
            i += 2
            continue
        if quote != "'" and (c == "`" or text.startswith("$(", i)):
            start = i + (1 if c == "`" else 2)
            end = text.find("`", start) if c == "`" else close_paren(text, start)
            end = len(text) if end < 0 else end
            subs.append(text[start:end])
            out.append("__SUB__")
            i = end + 1
            continue
        if c in "'\"" and quote in ("", c):
            quote = "" if quote else c
        elif not quote and c == "#" and (i == 0 or text[i - 1].isspace()):
            i = text.find("\n", i) if "\n" in text[i:] else len(text)
            continue
        out.append(" ; " if c == "\n" and not quote else c)
        i += 1
    return "".join(out), subs


def split_words(text: str) -> list[str]:
    lex = shlex.shlex(text, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        return list(lex)
    except ValueError:  # unbalanced quote: check it word by word all the same
        spaced = re.sub(r"([;&|()<>]+)", r" \1 ", text)
        return [w.strip("'\"") for w in spaced.split()]


def is_operator(word: str) -> bool:
    return bool(word) and all(c in "();<>|&" for c in word)


def check_command(text: str, cwd: str) -> None:
    bodies: list[str] = []
    check_shell(strip_heredocs(text, bodies), cwd, bodies)


def check_shell(text: str, cwd: str, bodies: list[str]) -> None:
    outer, subs = lift_subs(text)
    for sub in subs:
        check_shell(sub, cwd, bodies)
    simple: list[str] = []
    for word in [*split_words(outer), ";"]:
        if is_operator(word) and "<" not in word and ">" not in word:
            cwd = check_simple(simple, cwd, bodies)
            simple = []
        else:
            simple.append(word)


def strip_prefixes(words: list[str]) -> list[str]:
    while words:
        if words[0] in PREFIXES or words[:2] == ["uv", "run"]:
            words = words[2 if words[0] == "uv" else 1 :]
            while words and words[0].startswith("-") and words[0] != "-":
                words = words[2 if words[0] in PREFIX_VALUE_OPTS else 1 :]
        elif re.match(r"\w+=", words[0]):
            words = words[1:]
        else:
            break
    return words


def check_simple(tokens: list[str], cwd: str, bodies: list[str]) -> str:
    """Check one simple command; return the folder the next one runs in."""
    words: list[str] = []
    heredocs: list[str] = []
    i = 0
    while i < len(tokens):
        word, target = tokens[i], "".join(tokens[i + 1 : i + 2])
        if not is_operator(word):
            words.append(word)
            i += 1
            continue
        if words and words[-1].isdigit():
            words.pop()  # the 2 of 2>file
        mark = re.fullmatch(r"__HD(\d+)__", target)
        if word == "<<" and mark:
            heredocs.append(bodies[int(mark.group(1))])
        elif "<" not in word and not (word.endswith("&") and re.fullmatch(r"\d+|-", target)):
            guard(target, cwd, "a redirect")
        i += 2

    words = strip_prefixes(words)
    if not words:
        return cwd
    name, rest = os.path.basename(words[0]), words[1:]
    args = [w for w in rest if w and not w.startswith("-")]

    if name == "gh" and "--admin" in rest:
        raise Refused(ADMIN)
    if name in ("cd", "pushd"):
        return resolve("".join(args[:1]) or "~", cwd)
    if name == "git":
        check_git(rest)
    if name == "mise" and "repo:apply-settings" in rest:
        raise Refused(SETTINGS)
    script = "apply-github-settings.sh"
    runs = name == script or (name in ("bash", "sh") and any(w.endswith(script) for w in rest))
    if runs and "--check" not in rest:
        raise Refused(SETTINGS)
    if name in ("docker", "docker-compose"):
        sub = docker_sub(rest)
        if sub in DOCKER_BAD:
            raise Refused(DOCKER, sub)

    inline = [rest[n + 1] for n, w in enumerate(rest[:-1]) if w in ("-c", "-e")]
    if SCRIPTERS.fullmatch(name):
        for text in inline + heredocs:
            guard_script(text, f"a {name} script")
    elif name in ("bash", "sh"):
        for text in inline:
            check_shell(text, cwd, bodies)
        for text in heredocs:
            guard_script(text, f"a {name} script")
            check_command(text, cwd)
    elif name == "sqlite3":
        for text in heredocs:
            guard_script(text, "a sqlite3 script")
        for arg in [] if "-readonly" in rest else args:
            path, _, query = re.sub(r"^file:(//)?", "", arg).partition("?")
            if not (arg.startswith("file:") and "mode=ro" in query):
                guard(path, cwd, "sqlite3 without mode=ro or -readonly")

    targets: list[str] = []
    in_place = name == "sed" and any(re.match(r"-(-in-place|\w*i)", w) for w in rest)
    if name in WRITE_ANY or in_place:
        targets = args
    elif name in WRITE_LAST:
        flags = ("-t", "--target-directory")
        targets = [rest[n + 1] for n, w in enumerate(rest[:-1]) if w in flags]
        targets += [w.split("=", 1)[1] for w in rest if w.startswith("--target-directory=")]
        if name == "rsync" or not targets:
            targets = args[-1:] if len(args) > 1 else []
    elif name == "dd":
        targets = [w[3:] for w in rest if w.startswith("of=")]
    for target in targets:
        guard(target, cwd, name, parents=name in ("rm", "mv"))
    return cwd


def check_git(rest: list[str]) -> None:
    i = 0
    while i < len(rest) and rest[i].startswith("-"):
        i += 2 if rest[i] in ("-C", "-c", "--git-dir", "--work-tree", "--namespace") else 1
    sub, args = "".join(rest[i : i + 1]), rest[i + 1 :]
    if sub == "commit":
        args = commit_flags(args)
    shorts = [w[1:] for w in args if re.fullmatch(r"-[a-zA-Z]+", w)]
    # -n is --no-verify on a commit, a dry run on a push
    if "--no-verify" in args or (sub == "commit" and any("n" in s for s in shorts)):
        raise Refused(NO_VERIFY)
    if sub == "push":
        long = any(re.match(r"--(force|mirror)", w) for w in args)
        plus = any(w.startswith("+") for w in args)
        if long or plus or any("f" in s for s in shorts):
            raise Refused(FORCE)


def commit_flags(args: list[str]) -> list[str]:
    """The flags of a git commit, without the values of -m, -F and the like."""
    flags, i = [], 0
    while i < len(args) and args[i] != "--":
        word = args[i]
        i += 1
        if re.fullmatch(r"-[a-zA-Z]+", word):
            # letters after a flag that takes a value belong to the value
            head = re.split(r"[mFCctuS]", word[1:])[0]
            flags.append("-" + head)
            if len(head) == len(word) - 2 and word[-1] in "mFCct":
                i += 1
        elif word.startswith("--"):
            flags.append(word)
            if word in ("--message", "--file", "--reuse-message", "--reedit-message", "--author"):
                i += 1
    return flags


def docker_sub(rest: list[str]) -> str:
    i = 0
    while i < len(rest):
        word = rest[i]
        i += 2 if word in DOCKER_VALUE_OPTS else 1
        if not word.startswith("-") and word not in DOCKER_GROUPS:
            return word
    return ""


def main() -> None:
    call = json.loads(sys.stdin.read())
    tool, tool_input = call.get("tool_name"), call.get("tool_input") or {}
    cwd = call.get("cwd") or os.getcwd()
    if tool == "Bash":
        check_command(tool_input.get("command") or "", cwd)
    elif tool in ("Write", "Edit", "NotebookEdit"):
        path = tool_input.get("notebook_path" if tool == "NotebookEdit" else "file_path") or ""
        guard(path, cwd, tool)


if __name__ == "__main__":
    try:
        main()
    except Refused as refused:
        why, todo = str(refused), refused.todo
    except Exception as error:
        why = f"the hook crashed ({type(error).__name__}: {error}) and refuses what it cannot check"
        todo = "Tell the user about the crash."
    else:
        sys.exit(0)
    print(f"Refused by the fence (.claude/hooks/fence.py): {why}.\n{todo} {TAIL}", file=sys.stderr)
    sys.exit(2)
