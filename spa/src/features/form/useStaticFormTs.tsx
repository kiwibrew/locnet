import { get, set, isFunction } from 'lodash-es';
import { create, type StoreApi, type UseBoundStore } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  useCallback,
  useEffect,
  useRef,
  type FormEventHandler,
  type FormEvent,
} from 'react';
import { useShallow } from 'zustand/shallow';
import { produce, setAutoFreeze, type Draft } from 'immer';
import {
  type EditableForm,
  type EditableModel,
  type ModelRoot,
  type Node,
} from './node';
import type { ObjectPathDeep } from './path';
import { deepSearchByNodeFragment } from './node.utils';

// disable Zustand freezing objects which marks them readonly
setAutoFreeze(false);

export type Resolver<
  T extends EditableForm,
  M extends EditableModel,
  FormPath = ObjectPathDeep<T>,
  FormNodesPath = ObjectPathDeep<T['nodes']>,
  ModelPath = ObjectPathDeep<M>,
  ModelRootPath = ObjectPathDeep<M['root']>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  TAny = any,
> = (props: {
  immerForm: Draft<T>;
  formPath: FormPath;
  formNodesPath: FormNodesPath;
  immerModel: Draft<M>;
  modelPath?: ModelPath | undefined;
  modelRootPath?: ModelRootPath;
  newValue: TAny;
  previousValue: TAny;
  immerMeta: Draft<FormMeta>;
  getByLabelId: (labelId: string) => Node | undefined;
  getFormNodeByType: <Type extends Node['type']>(
    type: Type,
  ) => Extract<Node, { type: Type }> | undefined;
  setErrorByModelRootPath(
    modelRootPath: ModelRootPath,
    validityMessage: string | undefined,
  ): void;
  setFormAndModelValueByModelRootPath: <MRP extends ModelRootPath>(
    modelRootPath: MRP,
    value: unknown,
  ) => void;
  setFormAndModelValue: <FP extends FormPath, MRP extends ModelRootPath>(
    formPath: FP,
    modelRootPath: MRP,
    value: unknown,
  ) => void;
  queueFormSideEffect: (formPath: FormPath, promise: Promise<unknown>) => void;
}) => void;

type Props<
  T extends EditableForm,
  M extends EditableModel,
  FormPath = ObjectPathDeep<T>,
  FormNodesPath = ObjectPathDeep<T['nodes']>,
  ModelPath = ObjectPathDeep<M>,
  ModelRootPath = ObjectPathDeep<M['root']>,
> = {
  resolver: Resolver<T, M, FormPath, FormNodesPath, ModelPath, ModelRootPath>;
  defaultForm: T;
  defaultModel: M;
};

export type SubmitHandler<
  T extends EditableForm,
  M extends ModelRoot,
  FormPath = ObjectPathDeep<T>,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _FormNodesPath = ObjectPathDeep<T['nodes']>,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _ModelPath = ObjectPathDeep<M>,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _ModelRootPath = ObjectPathDeep<M['root']>,
> = (props: {
  form: T;
  model: M;
  immerForm: Draft<T>;
  immerModel: Draft<M>;
  queueFormSideEffect: (formPath: FormPath, promise: Promise<unknown>) => void;
}) => void;

export type UseStaticFormTsReturn<
  T extends EditableForm,
  M extends EditableModel,
  FormPath = ObjectPathDeep<T>,
  FormNodesPath = ObjectPathDeep<T['nodes']>,
  ModelPath = ObjectPathDeep<M>,
  ModelRootPath = ObjectPathDeep<M['root']>,
> = {
  useFormStore: UseBoundStore<StoreApi<T>>;
  useWatchFormStore: <U>(formPath: FormPath, defaultValue: U) => U;
  useWatchFormByNodeType: <T extends Node['type']>(
    nodeType: T,
  ) => Extract<Node, { type: T }> | undefined;
  useModelStore: UseBoundStore<StoreApi<M>>;
  useWatchModelStore: <U>(modelPath: ModelPath, defaultValue: U) => U;
  useFormAndModel: <V>(
    formPath: FormPath,
    modelPath: ModelRootPath | undefined,
    defaultValue: V,
    retainValueOnMount?: boolean,
  ) => [V, (value: V | ((value: V) => V)) => void];
  setModelAndFormByModelRoot: (
    modelRootPath: ModelRootPath,
    newValue: unknown,
    modelRootPathToFormPathMappings?: Record<string, FormPath>,
  ) => void;
  useHandleSubmit: (
    onSubmit: SubmitHandler<
      T,
      M,
      FormPath,
      FormNodesPath,
      ModelPath,
      ModelRootPath
    >,
  ) => FormEventHandler<HTMLFormElement>;
  handleInvalid: (e: FormEvent<HTMLFormElement>) => void;
  useFormMetaStore: UseBoundStore<StoreApi<FormMeta>>;
  waitForFormChange: <V>(formPath: FormPath, defaultValue: V) => Promise<V>;
  useWatchFormMetaStore: <K extends ObjectPathDeep<FormMeta>, V>(
    path: K,
    defaultValue: V,
  ) => V;
  getFormByNodeType: <T extends Node['type']>(
    nodeType: T,
  ) => Extract<Node, { type: T }> | undefined;
};

type FormMeta = {
  value: {
    isSubmitting: boolean;
  };
  set: <K extends ObjectPathDeep<FormMeta>>(path: K, value: unknown) => void;
};

export const useStaticFormTs = <
  T extends EditableForm,
  M extends EditableModel,
  FormPath = ObjectPathDeep<T>,
  FormNodesPath = ObjectPathDeep<T['nodes']>,
  ModelPath = ObjectPathDeep<M>,
  ModelRootPath = ObjectPathDeep<M['root']>,
>(
  props: Props<T, M, FormPath, FormNodesPath, ModelPath, ModelRootPath>,
): UseStaticFormTsReturn<
  T,
  M,
  FormPath,
  FormNodesPath,
  ModelPath,
  ModelRootPath
> => {
  const { resolver } = props;

  // Form value store
  const useFormStoreRef = useRef<UseBoundStore<StoreApi<T>>>(null);
  if (useFormStoreRef.current === null) {
    // this pattern because of https://react.dev/reference/react/useRef#avoiding-recreating-the-ref-contents
    // a conventional initialValue would recreate the store every render
    useFormStoreRef.current = create(
      devtools<T>(
        (zustandSet) =>
          // @ts-expect-error this needs better TS
          ({
            nodes: props.defaultForm.nodes,
            set: (formPath: FormPath, value: unknown) =>
              zustandSet((state: T) =>
                produce(state, (immerState: Draft<T>) => {
                  set(immerState as object, String(formPath), value);
                }),
              ),
            api: props.defaultForm.api,
          }) as UseBoundStore<StoreApi<T['nodes']>>,
        { name: 'locnet-form' },
      ),
    );
  }
  const { current: useFormStore } = useFormStoreRef;

  // Model store
  const useModelStoreRef = useRef<UseBoundStore<StoreApi<M>>>(null);
  if (useModelStoreRef.current === null) {
    // this pattern because of https://react.dev/reference/react/useRef#avoiding-recreating-the-ref-contents
    // a conventional initialValue would recreate the store every render
    useModelStoreRef.current = create(
      devtools(
        (zustandSet) =>
          // @ts-expect-error this needs better TS
          ({
            value: props.defaultModel.root,
            set: (modelPath: ModelPath, value: unknown) =>
              zustandSet((state: M) =>
                produce(state, (immerState: Draft<M>) => {
                  set(immerState, String(modelPath), value);
                }),
              ),
          }) as UseBoundStore<StoreApi<M>>,
        { name: 'locnet-model' },
      ),
    );
  }
  const { current: useModelStore } = useModelStoreRef;

  // Meta store
  const useFormMetaStoreRef = useRef<UseBoundStore<StoreApi<FormMeta>>>(null);
  if (useFormMetaStoreRef.current === null) {
    useFormMetaStoreRef.current = create(
      devtools(
        (zustandSet) =>
          // @ts-expect-error this needs better TS
          ({
            value: { isSubmitting: false },
            set: <K extends ObjectPathDeep<FormMeta>>(
              formMetaPath: K,
              value: unknown,
            ) =>
              zustandSet((state: FormMeta) =>
                produce(state, (immerState) => {
                  set(
                    immerState,
                    String(`${'value' as keyof FormMeta}.${formMetaPath}`),
                    value,
                  );
                }),
              ),
          }) as UseBoundStore<StoreApi<FormMeta>>,
        { name: 'locnet-meta' },
      ),
    );
  }
  const useFormMetaStore = useFormMetaStoreRef.current

  const useWatchModelStore = useCallback(
    <U,>(modelPath: ModelPath, defaultValue: U): U => {
      // error says useValue shouldn't be called in callbacks but this is a custom hook
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const watchedValue = useModelStore(
        // eslint-disable-next-line react-hooks/rules-of-hooks
        useShallow((state) => get(state, String(modelPath))),
      );
      return watchedValue ?? defaultValue;
    },
    [useModelStore],
  );

  const useWatchFormStore = useCallback(
    <U,>(formPath: FormPath, defaultValue: U): U => {
      // error says useValue shouldn't be called in callbacks but this is a custom hook
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const watchedValue = useFormStore(
        // eslint-disable-next-line react-hooks/rules-of-hooks
        useShallow((state) => get(state, String(formPath))),
      );
      return watchedValue ?? defaultValue;
    },
    [useFormStore],
  );

  const useWatchFormMetaStore = useCallback(
    <K extends ObjectPathDeep<FormMeta>, T>(path: K, defaultValue: T): T => {
      // error says useValue shouldn't be called in callbacks but this is a custom hook
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const selectedValue = useFormMetaStore(
        // eslint-disable-next-line react-hooks/rules-of-hooks
        useShallow((state) => {
          const selectedValue = get(state, String(path));
          return selectedValue;
        }),
      );
      return selectedValue ?? defaultValue;
    },
    [useFormMetaStore],
  );

  type SideEffect = { formPath: FormPath; promise: Promise<unknown> };
  const sideEffectsRef = useRef<SideEffect[]>([]);
  const queueFormSideEffect = useCallback(
    (formPath: SideEffect['formPath'], promise: SideEffect['promise']) => {
      sideEffectsRef.current.push({ formPath, promise });
    },
    [],
  );
  const processSideEffects = useCallback(async () => {
    const { current: handleResolverChange } = handleResolverChangeRef;
    if (!handleResolverChange) {
      console.error('Internal error. handleResolverChange unavailable.');
      return;
    }

    const { current: sideEffects } = sideEffectsRef;
    while (sideEffects.length > 0) {
      const sideEffect = sideEffects.pop();
      if (!sideEffect) {
        break;
      }
      const newValue = await sideEffect.promise;
      handleResolverChange(sideEffect.formPath, undefined, newValue);
    }
  }, []);

  const useHandleSubmit = useCallback(
    (
      onSubmit: SubmitHandler<
        T,
        M,
        FormPath,
        FormNodesPath,
        ModelPath,
        ModelRootPath
      >,
    ): FormEventHandler<HTMLFormElement> => {
      // error says useCallback shouldn't be called in callbacks but this is a custom hook
      // just one that is dynamically generated
      // eslint-disable-next-line react-hooks/rules-of-hooks
      return useCallback(
        async (e) => {
          const { target } = e;

          if (!(target instanceof HTMLFormElement)) {
            throw Error('Expected <form> element for e.target');
          }

          e.preventDefault();

          const isFormValid = target.reportValidity();

          if (!isFormValid) {
            console.log(
              "Is not valid. It shouldn't get this far unless valid so this shouldn't happen.",
            );
            return;
          }

          useFormMetaStore.getState().set('value.isSubmitting', true);

          const prevForm = useFormStore.getState();
          const prevModel = useModelStore.getState();
          let newForm = prevForm;
          let newModel = prevModel;

          newForm = produce(prevForm, (immerForm) => {
            newModel = produce(prevModel, (immerModel) => {
              onSubmit({
                form: prevForm,
                model: prevModel,
                immerForm,
                immerModel,
                queueFormSideEffect,
              });
            });
          });

          processSideEffects();

          if (newForm.nodes !== prevForm.nodes) {
            useFormStore.getState().set('nodes', newForm.nodes);
          }
          if (newModel.root !== prevModel.root) {
            useModelStore.getState().set('root', newModel.root);
          }
        },
        [onSubmit],
      );
    },
    [
      useFormStore,
      useModelStore,
      useFormMetaStore,
      queueFormSideEffect,
      processSideEffects,
    ],
  );

  const handleResolverChangeRef =
    useRef<
      (
        formPath: FormPath,
        modelRootPath: ModelRootPath | undefined,
        value: unknown,
      ) => void
    >(null);

  if (!handleResolverChangeRef.current) {
    handleResolverChangeRef.current = (formPath, modelRootPath, value) => {
      const newValue = isFunction(value)
        ? value(get(useFormStore.getState(), formPath as string))
        : value;

      let prevForm = useFormStore.getState();
      const previousValue = get(prevForm, formPath as string);
      prevForm.set(formPath as string, newValue);

      let prevModel = useModelStore.getState();
      if (modelRootPath !== undefined) {
        prevModel.set(`root.${modelRootPath}`, newValue);
      }

      const prevMeta = useFormMetaStore.getState();
      prevForm = useFormStore.getState();
      prevModel = useModelStore.getState();

      let newForm = prevForm;
      let newModel = prevModel;
      let newMeta = prevMeta;

      const formNodesPath = String(formPath).substring(
        0,
        ('nodes' satisfies keyof EditableForm).length,
      ) as FormNodesPath;

      const getByLabelId = (labelIntlId: string): Node | undefined =>
        deepSearchByNodeFragment(prevForm, 'labelIntlId', labelIntlId);

      const getFormNodeByType = <
        Type extends Node['type'],
        NodeByType = Extract<Node, { type: Type }>,
      >(
        type: Type,
      ): NodeByType | undefined =>
        deepSearchByNodeFragment(prevForm, 'type', type) as NodeByType;

      const setErrorByModelRootPath = (
        modelRootPath: ModelRootPath,
        validityMessage: string | undefined,
      ): void => {
        const { current: handleResolverChange } = handleResolverChangeRef;
        if (!handleResolverChange) {
          console.error('Internal error. handleResolverChange unavailable.');
          return;
        }

        const formPath =
          modelRootPathToFormPathRef.current[String(modelRootPath)];
        if (!formPath) {
          console.warn('No form path found for modelRootPath =', modelRootPath);
          return;
        }
        const formErrorPath = `${formPath}_error` as FormPath; // by convention, an '_error' suffix
        newForm.set(String(formErrorPath), validityMessage);
      };

      const setFormAndModelValue = (
        formPath: FormPath,
        modelRootPath: ModelRootPath | undefined,
        value: unknown,
      ) => {
        const newForm = useFormStore.getState();
        const newModel = useModelStore.getState();

        newForm.set(String(formPath), value);
        if (modelRootPath) {
          newModel.set(String(modelRootPath), value);
        }
      };

      const setFormAndModelValueByModelRootPath = <MRP extends ModelRootPath>(
        modelRootPath: MRP,
        value: unknown,
      ) => {
        const formPath =
          modelRootPathToFormPathRef.current[String(modelRootPath)];
        if (!formPath) {
          console.warn('No form path found for modelRootPath=', modelRootPath);
          return;
        }
        newForm.set(String(formPath), value);
        newModel.set(`root.${modelRootPath}`, value);
        // console.log("Setting form value", modelRootPath, formPath, value)
      };

      newForm = produce(prevForm, (immerForm) => {
        newModel = produce(prevModel, (immerModel) => {
          newMeta = produce(prevMeta, (immerMeta) => {
            resolver({
              immerForm,
              formPath,
              formNodesPath,
              immerModel,
              modelPath: `root.${modelRootPath}` as ModelPath,
              modelRootPath: modelRootPath,
              newValue,
              previousValue,
              immerMeta,
              getByLabelId,
              getFormNodeByType,
              setErrorByModelRootPath,
              setFormAndModelValueByModelRootPath,
              setFormAndModelValue,
              queueFormSideEffect,
            });
          });
        });
      });

      processSideEffects();

      if (newForm.nodes !== prevForm.nodes) {
        useFormStore.getState().set('nodes', newForm.nodes);
      }
      if (newModel.root !== prevModel.root) {
        useModelStore.getState().set('root', newModel.root);
      }
      if (newMeta.value !== prevMeta.value) {
        useFormMetaStore.getState().set('value', newMeta.value);
      }
    };
  }

  const modelRootPathToFormPathRef = useRef<Record<string, FormPath>>({});

  // Syncs changes to both form and model store
  const useFormAndModel = useCallback(
    <V,>(
      formPath: FormPath,
      modelRootPath: ModelRootPath | undefined,
      defaultValue: V,
      retainValueOnMount?: boolean,
    ): [V, (value: V | ((value: V) => V)) => void] => {
      if (modelRootPath) {
        modelRootPathToFormPathRef.current[String(modelRootPath)] = formPath;
      }
      // lint error isn't relevant: useCallback shouldn't be called in callbacks but this is a custom hook
      // just one that is dynamically generated
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const setter = useCallback(
        (value: V | ((value: V) => V)) => {
          const { current: handleResolverChange } = handleResolverChangeRef;
          if (!handleResolverChange) {
            console.error('Internal error. handleResolverChange unavailable.');
            return;
          }
          handleResolverChange(formPath, modelRootPath, value);
        },
        [formPath, modelRootPath],
      );
      // lint error isn't relevant: useEffect shouldn't be called in callbacks but this is a custom hook
      // just one that is dynamically generated
      // eslint-disable-next-line react-hooks/rules-of-hooks
      useEffect(() => {
        const formState = useFormStore.getState();
        const model = useModelStore.getState();
        const existingFormValue = get(formState, String(formPath));
        const modelPath = `root.${modelRootPath}`;
        const existingModelValue = get(model, modelPath);
        if (
          !retainValueOnMount ||
          (retainValueOnMount &&
            !existingFormValue &&
            (!modelRootPath || (modelRootPath && existingModelValue)))
        ) {
          setter(defaultValue);
        }
      }, [formPath, retainValueOnMount, modelRootPath, setter, defaultValue]);
      // error says useWatchFormStore shouldn't be called in callbacks but this is a custom hook
      // just one that is dynamically generated
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const value = useWatchFormStore(formPath, defaultValue);
      return [value, setter];
    },
    [handleResolverChangeRef, useFormStore, useModelStore, useWatchFormStore],
  );

  const setModelAndFormByModelRoot = useCallback(
    (
      modelRootPath: ModelRootPath,
      formValue: unknown,
      modelRootPathToFormPathMappings?: Record<string, FormPath>,
    ) => {
      if (modelRootPathToFormPathMappings) {
        console.log('adding mapping', modelRootPathToFormPathMappings);
        Object.entries(modelRootPathToFormPathMappings).forEach(
          ([modelRootPath, formPath]) => {
            const { current: mapping } = modelRootPathToFormPathRef;
            if (!mapping) {
              throw Error(
                'Expected to find modelRootPathToFormPathRefMappings',
              );
            }
            mapping[modelRootPath] = formPath;
            console.log('add mapping', modelRootPath, formPath);
          },
        );
      }

      const { current: handleResolverChange } = handleResolverChangeRef;
      if (!handleResolverChange) {
        console.error('Internal error. handleResolverChange unavailable.');
        return;
      }

      const formPath =
        modelRootPathToFormPathRef.current[String(modelRootPath)];
      if (!formPath) {
        console.warn(
          'setModelAndFormByModelRoot: No form path found for modelRootPath =',
          modelRootPath,
        );
        return;
      }
      handleResolverChange(formPath, modelRootPath, formValue);
    },
    [],
  );

  const handleInvalid = useCallback((e: FormEvent<HTMLFormElement>) => {
    const { target } = e;
    if (!(target instanceof HTMLElement)) {
      console.error('Expected HTML element');
      return;
    }

    const scrollIntoView = () => {
      target.scrollIntoView({
        block: 'center',
        inline: 'center',
      });
    };

    scrollIntoView();
  }, []);

  const waitForFormChange = useCallback(
    <V,>(
      formPath: FormPath,
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      _defaultValue: V,
    ) => {
      return new Promise<V>((resolve) => {
        const { current: formStore } = useFormStoreRef;
        if (!formStore) {
          throw Error('Expected form store');
        }
        const initialState = formStore.getState();
        const initialValue = get(initialState, String(formPath));

        const unsubscribe = formStore.subscribe((newState) => {
          const newValue = get(newState, String(formPath));
          if (newValue !== initialValue) {
            unsubscribe();
            resolve(newValue as V);
          }
        });
      });
    },
    [useFormStoreRef],
  );

  const useWatchFormByNodeType = useCallback(
    <T extends Node['type'], NodeByT = Extract<Node, { type: T }>>(
      nodeType: T,
    ): NodeByT | undefined => {
      // error says useValue shouldn't be called in callbacks but this is a custom hook
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const watchedValue = useFormStore(
        // eslint-disable-next-line react-hooks/rules-of-hooks
        useShallow(
          (state) =>
            deepSearchByNodeFragment(state, 'type', nodeType) as
              | NodeByT
              | undefined,
        ),
      );
      return watchedValue;
    },
    [useFormStore],
  );

  const getFormByNodeType = useCallback(
    <T extends Node['type'], NodeByT = Extract<Node, { type: T }>>(
      nodeType: T,
    ): NodeByT | undefined => {
      const state = useFormStore.getState();
      return deepSearchByNodeFragment(state, 'type', nodeType) as
        | NodeByT
        | undefined;
    },
    [useFormStore],
  );

  return {
    useFormStore,
    useWatchFormStore,
    useModelStore,
    useWatchModelStore,
    handleInvalid,
    useFormAndModel,
    setModelAndFormByModelRoot,
    useHandleSubmit,
    waitForFormChange,
    useFormMetaStore,
    useWatchFormMetaStore,
    useWatchFormByNodeType,
    getFormByNodeType,
  };
};
