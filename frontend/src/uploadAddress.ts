// A picture on a share preview is served under the link, so a visitor without an account can see
// the snapshot. Everywhere else it is the account's own upload, including the print, which sends
// its token as a header on `/api/uploads/`.
export function uploadAddress(id: number): string {
  const token = /^\/teilen\/([^/]+)/.exec(location.pathname)?.[1];
  return token ? `/api/shares/${decodeURIComponent(token)}/uploads/${id}` : `/api/uploads/${id}`;
}
