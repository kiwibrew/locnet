// eslint-disable-next-line @typescript-eslint/no-explicit-any
type DefinitelyNotAny = any

// https://stackoverflow.com/a/54265129
export function debouncePromise<T extends (...args: DefinitelyNotAny[]) => DefinitelyNotAny>(
  fn: T,
  wait: number,
  abortValue: DefinitelyNotAny = undefined,
) {
  let cancel = () => {};
  // type Awaited<T> = T extends PromiseLike<infer U> ? U : T
  type ReturnT = Awaited<ReturnType<T>>;
  const wrapFunc = (...args: Parameters<T>): Promise<ReturnT> => {
    cancel();
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => resolve(fn(...args)), wait);
      cancel = () => {
        clearTimeout(timer);
        if (abortValue !== undefined) {
          reject(abortValue);
        }
      };
    });
  };
  return wrapFunc;
}
