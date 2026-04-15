import type { FormPath, ModelPath } from './FormProvider';
import type { Node } from './node';

/**
 * Generates valid string paths for an object.
 * Based on react-hook-form TypeScript path code
 */
export type ObjectPathDeep<TFieldValues> = Path<TFieldValues>;

type Primitive = null | undefined | string | number | boolean | symbol | bigint;

type ArrayKey = number;

type BrowserNativeObject = Date | FileList | File;

type IsEqual<T1, T2> = T1 extends T2
  ? (<G>() => G extends T1 ? 1 : 2) extends <G>() => G extends T2 ? 1 : 2
    ? true
    : false
  : false;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type DefinitelyNotAny = any;

type IsTuple<T extends ReadonlyArray<DefinitelyNotAny>> =
  number extends T['length'] ? false : true;

type AnyIsEqual<T1, T2> = T1 extends T2
  ? IsEqual<T1, T2> extends true
    ? true
    : never
  : never;

type TupleKeys<T extends ReadonlyArray<DefinitelyNotAny>> = Exclude<
  keyof T,
  keyof DefinitelyNotAny[]
>;

type PathImpl<K extends string | number, V, TraversedTypes> = V extends
  | Primitive
  | BrowserNativeObject
  ? `${K}`
  : true extends AnyIsEqual<TraversedTypes, V>
    ? `${K}`
    : `${K}` | `${K}.${PathInternal<V, TraversedTypes | V>}`;

type PathInternal<T, TraversedTypes = T> =
  T extends ReadonlyArray<infer V>
    ? IsTuple<T> extends true
      ? {
          [K in TupleKeys<T>]-?: PathImpl<K & string, T[K], TraversedTypes>;
        }[TupleKeys<T>]
      : PathImpl<ArrayKey, V, TraversedTypes>
    : {
        [K in keyof T]-?: PathImpl<K & string, T[K], TraversedTypes>;
      }[keyof T];

type Path<T> = T extends DefinitelyNotAny ? PathInternal<T> : never;

export const modelPathJoin = <T extends Node>(id: string, prop: keyof T) => {
  return `${id}.${prop.toString()}` as ModelPath;
};

export const formPathJoin = <T extends Node>(id: string, prop: keyof T) => {
  return `${id}.${prop.toString()}` as FormPath;
};
