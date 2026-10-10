# Corpus

Old sheets and templates as teachers stored them, blanked. The suite opens, saves and prints each.

`scripts/corpus.py` wrote every file here from a read-only copy of the live database:

```sh
uv run python scripts/corpus.py copy.db tests/corpus/
```

Do not edit a file by hand. A string stays only where the script's `ALLOW` keeps it: a block's id, kind, colour, font and the like. In every other string a letter is now x and a digit 0. Numbers stay, so each block keeps its place and size. A picture would show upload 0.

With `BLATTWERK_CORPUS_SOURCE=copy.db` the suite also looks for every word of the copy in this folder, this page too. Should it find one here, reword this page.
