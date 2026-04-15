import { z } from 'zod';
import { type ObjectPathDeep } from './path';
import { DisclosureSchema } from './NodeTypes/Disclosure';
import { InertSchema } from './NodeTypes/Inert';
import { SubmitButtonSchema } from './NodeTypes/SubmitButton';
import { CountriesDropdownSchema } from './NodeTypes/CountriesDropdown';
import {
  TableFormSchema,
  TableFormColumnTextSchema,
  TableFormRowHeaderSchema,
  TableFormRowCellsSchema,
  TableFormCellTextSchema,
  TableFormCellInputNumberSchema,
  TableFormCellInputTextSchema,
} from './NodeTypes/TableForm';
import { CategoryTableFormSchema } from './NodeTypes/CategoryTableForm';
import { ToggleButtonSchema } from './NodeTypes/ToggleButton';
import { TechnologiesSchema } from './NodeTypes/Technologies';
import { FrequenciesSchema } from './NodeTypes/Frequencies';
import { TerrainSchema } from './NodeTypes/Terrain';
import { VegetationSchema } from './NodeTypes/Vegetation';
import { SelectSchema } from './NodeTypes/Select';
import { FieldHelpSchema } from './NodeTypes/FieldHelp';
import { RadioToggleButtonsSchema } from './NodeTypes/RadioToggleButtons';
import { OrganisationTypeSchema } from './NodeTypes/OrganisationType';
import { NetworkElementsSchema } from './NodeTypes/NetworkElements';
import { TextSchema } from './NodeTypes/Text';
import { HTMLSchema } from './NodeTypes/Html';
import { LoadingSchema } from './NodeTypes/Loading';
import { ExportTableSchema } from './NodeTypes/ExportTable';
import { ExportDetailedResultsSchema } from './NodeTypes/ExportDetailedResults';
import { ExportScatterChartSchema } from './NodeTypes/ExportScatterChart';
import { DataTableSchema } from './NodeTypes/DataTable';
import { ObjectTableSchema } from './NodeTypes/ObjectTable';
import { ExportFilesSchema } from './NodeTypes/ExportFiles';

export const NodeSchema = z.union([
  TextSchema,
  HTMLSchema,
  DisclosureSchema,
  InertSchema,
  CountriesDropdownSchema,
  SubmitButtonSchema,
  TableFormSchema,
  TableFormColumnTextSchema,
  TableFormRowHeaderSchema,
  TableFormRowCellsSchema,
  TableFormCellTextSchema,
  TableFormCellInputTextSchema,
  TableFormCellInputNumberSchema,
  CategoryTableFormSchema,
  ToggleButtonSchema,
  TechnologiesSchema,
  FrequenciesSchema,
  TerrainSchema,
  VegetationSchema,
  SelectSchema,
  FieldHelpSchema,
  RadioToggleButtonsSchema,
  OrganisationTypeSchema,
  NetworkElementsSchema,
  LoadingSchema,
  DataTableSchema,
  ExportTableSchema,
  ExportDetailedResultsSchema,
  ExportScatterChartSchema,
  ObjectTableSchema,
  ExportFilesSchema
]);

export type Node = z.infer<typeof NodeSchema>;

export const NodesSchema = NodeSchema.array().optional();

export type Nodes = z.infer<typeof NodesSchema>;

export type Root = { nodes: Nodes; api: Record<string, unknown> };

export type EditableForm = Root & {
  set(path: string, value: unknown): void;
};

export type GetRootPaths<T> = ObjectPathDeep<T>;

export type NodeProps<T extends Node> = {
  formPath: string;
  node: T;
};

// Utility type to replace Node
type ReplaceNodeValues<
  T,
  E = T extends Node ? Extract<Node, { type: T['type'] }> : never,
> = {
  -readonly [K in keyof T]: FormEditableWalker<T[K]>;
} & E;

// main type to replace Node values
type FormEditableWalker<T> = T extends Node
  ? ReplaceNodeValues<T>
  : T extends object
    ? {
        -readonly [K in keyof T]: FormEditableWalker<T[K]>;
      }
    : T;

// expands object types recursively for readabillity (shouldn't not affect types)
export type ExpandRecursively<T> = T extends object
  ? T extends infer O
    ? { -readonly [K in keyof O]: ExpandRecursively<O[K]> }
    : never
  : T;

export type MakeStaticFormTSValue<T extends Root> = ExpandRecursively<
  FormEditableWalker<T>
> & { set(formPath: GetRootPaths<T>, value: unknown): void };

export const makeStaticFormTSValue = <T extends Root>(root: T) =>
  ({
    nodes: structuredClone(root.nodes),
    set: (formPath: GetRootPaths<T>, value: unknown) => {
      console.error(
        `Ignoring set() called before initialisation with values`,
        formPath,
        value,
      );
    },
    api: root.api,
  }) as MakeStaticFormTSValue<T>;

export type MakeStaticFormTSModel<TModelRoot extends ModelRoot> = {
  root: TModelRoot['root'];
} & { set(formPath: string, value: unknown): void };

export const makeStaticFormTSModel = <MR extends ModelRoot>(value: MR) =>
  ({
    root: value.root,
    set: (formPath: string, value: unknown) => {
      console.error(
        `Ignoring set() called before initialisation with values`,
        formPath,
        value,
      );
    },
  }) as MakeStaticFormTSModel<MR>;

export type ModelRoot = { root: Record<string, unknown> };

export type EditableModel = {
  root: ModelRoot['root'];
  set(modelPath: string, value: unknown): void;
};
