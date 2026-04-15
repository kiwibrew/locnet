import { sha512 } from '@noble/hashes/sha2.js';
import { bytesToHex } from '@noble/hashes/utils.js';

export const hashString = (source: unknown): string => {
  const data = Uint8Array.from(JSON.stringify(source));
  const digest = sha512.create().update(data).digest();
  return bytesToHex(digest);
}
