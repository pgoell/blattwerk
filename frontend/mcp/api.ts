// HTTP to the Blattomat API as one teacher's token. Every error text goes through hide(), so the token never shows.
export function connect(base: string, token: string) {
  const hide = (text: string) => text.replaceAll(token, "***");

  async function send(method: string, path: string, body?: unknown): Promise<{ status: number; body: any }> {
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    return reply(method, path, {
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  // A picture as multipart form data, field `file`, the way the editor sends one.
  async function upload(data: Buffer, type: string): Promise<{ status: number; body: any }> {
    const form = new FormData();
    form.append("file", new Blob([new Uint8Array(data)], { type }), "bild");
    return reply("POST", "/uploads", { headers: { Authorization: `Bearer ${token}` }, body: form });
  }

  async function reply(method: string, path: string, init: RequestInit): Promise<{ status: number; body: any }> {
    let res: Response;
    try {
      res = await fetch(`${base}/api${path}`, { method, ...init });
    } catch (e) {
      throw new Error(hide(`Cannot reach Blattomat at ${base}: ${(e as Error).message}`));
    }
    const text = await res.text();
    try {
      return { status: res.status, body: JSON.parse(text) };
    } catch {
      return { status: res.status, body: text };
    }
  }

  async function bytes(path: string): Promise<{ status: number; body: string }> {
    let res: Response;
    try {
      res = await fetch(`${base}/api${path}`, { headers: { Authorization: `Bearer ${token}` } });
    } catch (e) {
      throw new Error(hide(`Cannot reach Blattomat at ${base}: ${(e as Error).message}`));
    }
    const buf = Buffer.from(await res.arrayBuffer());
    if (res.status !== 200) return { status: res.status, body: hide(buf.toString("utf8")) };
    return { status: res.status, body: buf.toString("base64") };
  }

  return { hide, send, bytes, upload };
}

export type Api = ReturnType<typeof connect>;
