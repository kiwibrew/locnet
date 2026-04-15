import { type EditableModel, type EditableForm } from './node';
import { createContext, useContext } from 'react';
import { type UseStaticFormTsReturn } from './useStaticFormTs';
import { type ObjectPathDeep } from './path';

export type FormPath = ObjectPathDeep<EditableForm>;
export type FormNodesPath = ObjectPathDeep<EditableForm["nodes"]>;
export type ModelPath = ObjectPathDeep<EditableModel>;
export type ModelRootPath = ObjectPathDeep<EditableModel["root"]>;

export const StaticFormTsContext = createContext<UseStaticFormTsReturn<
  EditableForm,
  EditableModel,
  FormPath,
  FormNodesPath,  
  ModelPath,
  ModelRootPath
> | null>(null);

export const StaticFormTsProvider = StaticFormTsContext.Provider;

export const useStaticFormTsContext = () => {
  const value = useContext(StaticFormTsContext);
  if (value === null) {
    throw Error(
      'useStaticFormTsContext called outside <StaticFormTsProvider> wrapper',
    );
  }
  return value;
};
