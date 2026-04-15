import type { WritableDraft } from 'immer';
import { type NetworkElement } from '../form/NodeTypes/NetworkElements';
import { makeStaticFormTSModel } from '../form/node';
import { type ObjectPathDeep } from '../form/path';
import type { BuilderInput, DefaultsDetail } from './api-generated-client';
import type { EditableLocNetForm } from './formData';

export type LocNetModelOmitLocations = Omit<BuilderInput, 'locations'>

export type LocNetModel = LocNetModelOmitLocations & {
  locations: NetworkElement[];
};

type LocNetModelTags = 'community_characteristics';

export type LocNetModelPath = ObjectPathDeep<LocNetModel> | LocNetModelTags;

export type ModelMapping = Record<string, LocNetModelPath>;

export const editableLocNetModel = makeStaticFormTSModel({
  root: {} as LocNetModel,
});

export type EditableLocNetModel = typeof editableLocNetModel;

export const isApiCharacteristicsDefaultsDetailArray = (characteristics: WritableDraft<EditableLocNetForm["api"]["characteristics"]>): characteristics is DefaultsDetail[] => {
  return Array.isArray(characteristics)
}