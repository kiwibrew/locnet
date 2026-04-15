import { z } from 'zod';
import { formPathJoin } from '../path';
import { FormNodeSchema } from '../base';
import { type NodeProps } from '../node';
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  type ChangeEvent,
} from 'react';
import {
  useStaticFormTsContext,
  type FormPath,
  type ModelPath,
} from '../FormProvider';
import styles from './NetworkElements.module.css';
import {
  networkTypesDataFromDOM,
  newBlankLocation,
  newBlankNetworkType,
  newBlankMidhaulLink,
  newBlankBackhaulLink,
  towerTypesDataFromDOM,
  midhaulDataFromDOM,
  backhaulDataFromDOM,
  powerTypesFromDOM,
  newLocationName,
  techDataFromDOM,
} from './NetworkElements.utils';
import { Text } from '../Intl';
import { useIntlIdOrText } from '../Intl.utils';
import { removeSoftDeletes } from '../softDeletes';
import { useCustomErrorRef } from '../useCustomError';
import { NBSP } from '../../../utils/strings';
import { clamp } from 'lodash-es';

export const BackhaulLinkSchema = z.object({
  key: z.string(),
  isSoftDeleted: z.boolean(),
  index: z.number(),
  type: z.string(),
  name: z.string(),
  monthlyCharge: z.string(),
  trafficCost_USD: z.string(),
});

export type BackhaulLink = z.infer<typeof BackhaulLinkSchema>;

export const MidhaulLinkSchema = z.object({
  key: z.string(),
  index: z.number(),
  isSoftDeleted: z.boolean(),
  type: z.string(),
  name: z.string(),
});
export type MidhaulLink = z.infer<typeof MidhaulLinkSchema>;

export const NetworkTypeSchema = z.object({
  key: z.string(),
  isSoftDeleted: z.boolean(),
  index: z.number(),
  type: z.string(),
  unitCount: z.string(),
});

export type NetworkType = z.infer<typeof NetworkTypeSchema>;

const TowerTypeSchema = z.object({
  name: z.string(),
  cost_USD: z.string(),
});

type TowerType = z.infer<typeof TowerTypeSchema>;

export const NetworkElementSchema = FormNodeSchema.extend({
  type: z.literal('NetworkElement'),
  isSoftDeleted: z.boolean(),
  index: z.number(),
  number: z.number(),
  location_name: z.string(),
  location_name_error: z.string().optional(),
  networkTypes: NetworkTypeSchema.array(),
  towerType: TowerTypeSchema,
  midhaulLink: MidhaulLinkSchema.array(),
  backhaulLinks: BackhaulLinkSchema.array(),
  power_type: z.string().nullable().optional(),
});

export type NetworkElement = z.infer<typeof NetworkElementSchema>;

export const NetworkElementsSchema = FormNodeSchema.extend({
  type: z.literal('NetworkElements'),
  locations: NetworkElementSchema.array(),
  modelPath: z.string().optional(),
});

export type NetworkLocations = z.infer<typeof NetworkElementsSchema>;

type Props = NodeProps<NetworkLocations>;

export const RenderNetworkElements = ({ node, formPath }: Props) => {
  const { useFormAndModel } = useStaticFormTsContext();
  const locationsId = formPathJoin<NetworkLocations>(formPath, 'locations');
  const networkLocationsCountRef = useRef<HTMLInputElement>(null);
  const [networkLocations, setNetworkLocations] = useFormAndModel(
    locationsId,
    node.modelPath as ModelPath,
    node.locations,
  );
  const locationsCountId = `${locationsId}.length`;

  const handleAdd = useCallback(() => {
    setNetworkLocations((prevLocations) => {
      const nonSoftDeletedLocations = removeSoftDeletes(prevLocations);
      return [
        ...prevLocations,
        newBlankLocation(prevLocations.length, {
          location_name: newLocationName(nonSoftDeletedLocations),
        }),
      ];
    });
  }, [setNetworkLocations]);

  const canDelete = networkLocations
    ? networkLocations.filter(
        (networkLocation) => !networkLocation.isSoftDeleted,
      ).length > 1
    : false;

  const networkCountIsValid =
    networkLocations.filter((networkLocation) => !networkLocation.isSoftDeleted)
      .length > 0;

  const networkCountInvalidMessage = useIntlIdOrText(
    'alert_add_one_location',
    undefined,
  );

  useEffect(() => {
    const { current: networkLocationsCount } = networkLocationsCountRef;
    if (
      !networkLocationsCount ||
      !(networkLocationsCount instanceof HTMLInputElement)
    ) {
      console.error(
        'Expected to find networkLocationsCountRef',
        networkLocationsCountRef,
      );
      return;
    }

    if (!networkCountIsValid) {
      const errorText = networkCountInvalidMessage ?? 'Field error';
      networkLocationsCount.setCustomValidity(errorText);
    } else {
      console.log('setting valid');
      networkLocationsCount.setCustomValidity(
        '', // setting empty string indicates to browser field validity
      );
    }
  }, [
    networkLocationsCountRef,
    networkCountIsValid,
    networkCountInvalidMessage,
  ]);

  return (
    <>
      <p className={styles.networkLocationsIntro}>
        <Text intlId="net_elements_desc" />
      </p>
      <p className={styles.numberOfLocationsIntro}>
        Number of locations:
        <input
          ref={networkLocationsCountRef}
          id={locationsCountId}
          name={locationsCountId}
          type="text"
          className={styles.networkCountBox}
          value={networkLocations.length}
        />
      </p>
      {networkLocations
        ?.filter((networkLocation) => !networkLocation.isSoftDeleted)
        .map((networkLocation) => {
          const newId = `${locationsId}.${networkLocation.index}` as FormPath;
          const newModedPath =
            `locations.${networkLocation.index}` as ModelPath;
          return (
            <RenderNetworkLocation
              id={newId}
              key={networkLocation.number}
              networkLocation={networkLocation}
              canDelete={canDelete}
              modelPath={newModedPath}
            />
          );
        })}
      <div className={styles.addContainer}>
        <button type="button" onClick={handleAdd} className={styles.addButton}>
          Add Network Location
        </button>
      </div>
      <ValidationErrors node={node} formPath={formPath} />
    </>
  );
};

type RenderNetworkLocationProps = {
  id: FormPath;
  modelPath: ModelPath;
  networkLocation: NetworkElement;
  canDelete: boolean;
};

const RenderNetworkLocation = ({
  id,
  modelPath,
  networkLocation,
  canDelete,
}: RenderNetworkLocationProps) => {
  const { useFormAndModel } = useStaticFormTsContext();
  const isSoftDeletedId = `${id}.${
    'isSoftDeleted' satisfies keyof NetworkElement
  }` as FormPath;
  const isSoftDeletedModelPath = `${modelPath}.${
    'isSoftDeleted' satisfies keyof NetworkElement
  }` as ModelPath;

  const nameId = `${id}.${
    'location_name' satisfies keyof NetworkElement
  }` as FormPath;
  const nameErrorPath = `${id}.${
    'location_name_error' satisfies keyof NetworkElement
  }` as FormPath;

  const nameModelPath = `${modelPath}.${
    'location_name' satisfies keyof NetworkElement
  }` as ModelPath;

  const powerTypeId =
    `${id}.${'power_type' satisfies keyof NetworkElement}` as FormPath;
  const powerTypeModelPath =
    `${modelPath}.${'power_type' satisfies keyof NetworkElement}` as ModelPath;

  const towerTypeId = `${id}.${'towerType' satisfies keyof NetworkElement}`;
  const towerTypeModelPath = `${modelPath}.${
    'towerType' satisfies keyof NetworkElement
  }`;

  const networkTypesId = `${id}.${
    'networkTypes' satisfies keyof NetworkElement
  }` as FormPath;
  const networkTypesModelPath = `${modelPath}.${
    'networkTypes' satisfies keyof NetworkElement
  }` as ModelPath;

  const [name, setName] = useFormAndModel(
    nameId,
    nameModelPath,
    networkLocation.location_name,
  );

  const [, setIsSoftDeleted] = useFormAndModel(
    isSoftDeletedId,
    isSoftDeletedModelPath,
    false,
  );

  const handleDelete = useCallback(() => {
    setIsSoftDeleted(true);
  }, [setIsSoftDeleted]);

  const handleEditName = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLInputElement)) {
        throw Error('expected <input>');
      }
      setName(target.value);
    },
    [setName],
  );

  const customErrorRef = useCustomErrorRef(nameErrorPath);

  return (
    <div className={styles.locationContainer} id={id}>
      {canDelete && (
        <button
          type="button"
          onClick={handleDelete}
          className={styles.deleteNetworkLocationButton}
        >
          &times;
        </button>
      )}

      <h2 className={styles.locationTitle}>{name}</h2>

      <label className={styles.nameContainer}>
        <span className={styles.labelWidth}>Name: </span>
        <input
          ref={customErrorRef}
          id={nameId}
          name={nameId}
          type="text"
          value={name}
          onChange={handleEditName}
          className={styles.locationNameInput}
        />
      </label>

      <RenderNetworkTypes
        id={networkTypesId}
        modelPath={networkTypesModelPath}
        defaultValue={networkLocation.networkTypes}
      />

      <RenderPowerSystem
        id={powerTypeId}
        modelPath={powerTypeModelPath}
        defaultValue={networkLocation.power_type ?? undefined}
      />

      <RenderTowerTypes id={towerTypeId} modelPath={towerTypeModelPath} />

      <RenderMidhaulAndBackhaul
        id={id}
        modelPath={modelPath}
        networkLocation={networkLocation}
      />
    </div>
  );
};

type RenderNetworkTypesProps = {
  id: FormPath;
  modelPath: ModelPath;
  defaultValue: NetworkType[];
};

const RenderNetworkTypes = ({
  id,
  modelPath,
  defaultValue,
}: RenderNetworkTypesProps) => {
  const { useFormAndModel } = useStaticFormTsContext();

  const [networkTypes, setNetworkTypes] = useFormAndModel(
    id,
    modelPath,
    defaultValue,
  );

  const handleAddNetworkType = useCallback(() => {
    setNetworkTypes((prevNetworkTypes) => [
      ...prevNetworkTypes,
      newBlankNetworkType(prevNetworkTypes.length),
    ]);
  }, [setNetworkTypes]);

  return (
    <div className={styles.networkTypesContainer}>
      <h3 className={styles.networkTypesHeading}>
        <Text intlId="net_types" />
      </h3>
      <p className={styles.networkTypesDescription}>
        <Text intlId="net_types_desc" />
      </p>

      {networkTypes
        .filter((networkType) => !networkType.isSoftDeleted)
        .map((networkType) => {
          const newId = `${id}.${networkType.index}` as FormPath;
          const newModelPath = `${modelPath}.${networkType.index}` as ModelPath;
          return (
            <RenderNetworkType
              key={networkType.key}
              id={newId}
              modelPath={newModelPath}
              networkType={networkType}
            />
          );
        })}

      <button
        type="button"
        onClick={handleAddNetworkType}
        className={styles.addButton}
      >
        <Text intlId="add" />
        {NBSP}
        <Text intlId="net_type" />
      </button>
    </div>
  );
};

type RenderNetworkTypeProps = {
  id: FormPath;
  modelPath: ModelPath;
  networkType: NetworkType;
};

const RenderNetworkType = ({
  id,
  modelPath,
  networkType,
}: RenderNetworkTypeProps) => {
  const { useFormAndModel, useWatchFormByNodeType } = useStaticFormTsContext();
  const typeId = `${id}.${'type' satisfies keyof NetworkType}` as FormPath;
  const typeModelPath = `${modelPath}.${
    'type' satisfies keyof NetworkType
  }` as ModelPath;
  const [typeValue, setType] = useFormAndModel(typeId, typeModelPath, '');
  const unitCountId = `${id}.${
    'unitCount' satisfies keyof NetworkType
  }` as FormPath;
  const unitCountModelPath = `${modelPath}.${
    'unitCount' satisfies keyof NetworkType
  }` as ModelPath;
  const [unitCount, setUnitCount] = useFormAndModel(
    unitCountId,
    unitCountModelPath,
    networkType.unitCount,
  );

  const handleChangeType = useCallback(
    (e: ChangeEvent<HTMLSelectElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLSelectElement)) {
        throw Error('expected <select>');
      }
      setType(target.value);
    },
    [setType],
  );

  const handleChangeUnitCount = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLInputElement)) {
        throw Error('expected <input>');
      }
      setUnitCount(target.value);
    },
    [setUnitCount],
  );

  const isSoftDeletedId = `${id}.${
    'isSoftDeleted' satisfies keyof NetworkType
  }` as FormPath;
  const isSoftDeletedModelId = `${modelPath}.${
    'isSoftDeleted' satisfies keyof NetworkType
  }` as ModelPath;
  const [, setSoftDeleted] = useFormAndModel(
    isSoftDeletedId,
    isSoftDeletedModelId,
    false,
  );

  type SelectOption = { value: string; label: string };

  const maybeTechnologies = useWatchFormByNodeType('Technologies');
  const maybeFrequencies = useWatchFormByNodeType('Frequencies');

  const options = useMemo((): SelectOption[] => {
    const networkTypeToSelectOption = (
      networkType: (typeof networkTypesDataFromDOM)[number],
    ): SelectOption => {
      return {
        label: networkType.network_type,
        value: networkType.network_type,
      };
    };

    return networkTypesDataFromDOM
      .filter((networkType): boolean => {
        if (
          maybeTechnologies?.children?.some((node) => {
            return (
              node.type === 'ToggleButton' &&
              node.value === networkType.technology &&
              !node.checked
            );
          })
        ) {
          return false;
        }

        if (
          maybeFrequencies?.children?.some(
            (node) =>
              node.type === 'ToggleButton' &&
              parseFloat(node.value) === networkType.frequency &&
              !node.checked,
          )
        ) {
          return false;
        }
        return true;
      })
      .map(networkTypeToSelectOption);
  }, [maybeTechnologies, maybeFrequencies]);

  useEffect(() => {
    // ensure typeValue is still valid
    const matchedValue = options.find(
      (networkType) => networkType.value === typeValue,
    );

    let timer: ReturnType<typeof setTimeout> | undefined = undefined;

    if (!matchedValue) {
      const newValue = options.length > 0 ? options[0].value : '';
      // DEBUG
      // console.log(
      //   'Network option ',
      //   typeValue,
      //   ' not available from ',
      //   options.map((networkType) => networkType.value),
      //   ' so setting to',
      //   newValue,
      //   '. Find result was',
      //   matchedValue,
      // );
      timer = setTimeout(() => setType(newValue), 100);
    } else {
      // DEBUG
      // console.log(
      //   'Network option ',
      //   typeValue,
      //   ' found at ',
      //   matchedValue,
      //   ' from ',
      //   options.map((networkType) => networkType.value),
      //   ' so not changing value',
      // );
    }

    return () => {
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [options, typeValue, setType]);

  const handleDelete = useCallback(() => {
    setSoftDeleted(true);
  }, [setSoftDeleted]);

  const selectedNetworkType = techDataFromDOM.find(
    (techDataItem) => techDataItem.network_type === typeValue,
  );

  useEffect(() => {
    if (!selectedNetworkType) {
      return;
    }
    let timer: ReturnType<typeof setTimeout> | undefined = undefined;
    const unitCountNumber = parseFloat(unitCount);
    const clampedValue = clamp(
      unitCountNumber,
      selectedNetworkType.min,
      selectedNetworkType.max,
    );
    if (clampedValue !== unitCountNumber) {
      timer = setTimeout(() => setUnitCount(clampedValue.toString()), 100);
    }

    return () => {
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [unitCount, selectedNetworkType, setUnitCount]);

  return (
    <div className={styles.networkTypeContainer}>
      <label>
        <select
          value={typeValue}
          onChange={handleChangeType}
          className={styles.networkTypeSelect}
        >
          {options.length > 0 && (
            <option value="" disabled>
              <Text intlId="sel" />
              {NBSP}
              <Text intlId="net_type" />
            </option>
          )}
          {options.map((option) => {
            return <option value={option.value}>{option.label}</option>;
          })}
        </select>
      </label>

      <label>
        <input
          id={unitCountId}
          name={unitCountId}
          type="number"
          min={selectedNetworkType?.min}
          max={selectedNetworkType?.max}
          value={unitCount}
          onChange={handleChangeUnitCount}
          className={styles.unitCountInput}
        />

        {selectedNetworkType && (
          <span className={styles.networkTypeUnitContainer}>
            {selectedNetworkType.unit}(s)
          </span>
        )}
      </label>

      <button
        type="button"
        onClick={handleDelete}
        className={styles.deleteNetworkTypeButton}
      >
        <Text intlId="remove" text="Remove" />
      </button>
    </div>
  );
};

type RenderPowerSystemProps = {
  id: FormPath;
  modelPath: ModelPath;
  defaultValue?: string;
};

const RenderPowerSystem = ({
  id,
  modelPath,
  defaultValue,
}: RenderPowerSystemProps) => {
  const { useFormAndModel } = useStaticFormTsContext();

  const [powerSystem, setPowerSystem] = useFormAndModel(
    id,
    modelPath,
    defaultValue ?? '',
  );

  const handlePowerTypeChange = useCallback(
    (e: ChangeEvent<HTMLSelectElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLSelectElement)) {
        throw Error('expected <select>');
      }
      setPowerSystem(target.value);
    },
    [setPowerSystem],
  );

  return (
    <div className={styles.powerSystemContainer}>
      <h3 className={styles.powerSystemHeading}>
        <Text intlId="power_system" />
      </h3>
      <p className={styles.powerSystemDescription}>
        <Text intlId="power_system_desc" />
      </p>
      <select
        value={powerSystem}
        onChange={handlePowerTypeChange}
        className={styles.powerSystemSelect}
      >
        <option value="" disabled>
          <Text intlId="sel" />
          {NBSP}
          <Text intlId="power_system" />
        </option>
        {powerTypesFromDOM.map((item) => (
          <option value={item.element}>
            <Text intlId={item.element} />
            {': '}
            {NBSP}
            <Text intlId={item.description} />
          </option>
        ))}
      </select>
    </div>
  );
};

type RenderTowerTypesProps = {
  id: string;
  modelPath: string;
};

const RenderTowerTypes = ({ id, modelPath }: RenderTowerTypesProps) => {
  const { useFormAndModel } = useStaticFormTsContext();
  const towerTypeNameId = `${id}.${
    'name' satisfies keyof TowerType
  }` as FormPath;
  const towerTypeNameModelPath = `${modelPath}.${
    'name' satisfies keyof TowerType
  }` as ModelPath;
  const [towerTypeName, setTowerTypeName] = useFormAndModel(
    towerTypeNameId,
    towerTypeNameModelPath,
    '',
  );
  const towerTypeCost_USD_Id = `${id}.${
    'cost_USD' satisfies keyof TowerType
  }` as FormPath;
  const towerTypeCost_USD_modelPath = `${modelPath}.${
    'cost_USD' satisfies keyof TowerType
  }` as ModelPath;
  const [towerTypeCost_USD, setTowerTypeCost_USD] = useFormAndModel(
    towerTypeCost_USD_Id,
    towerTypeCost_USD_modelPath,
    towerTypesDataFromDOM[0].value.toString(),
  );

  const handleTowerTypeChange = useCallback(
    (e: ChangeEvent<HTMLSelectElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLSelectElement)) {
        throw Error('expected <select>');
      }
      setTowerTypeName(target.value);
      // also set cost
      setTowerTypeCost_USD(target.value);
    },
    [setTowerTypeName, setTowerTypeCost_USD],
  );

  const handleCostChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLInputElement)) {
        throw Error('expected <input>');
      }
      setTowerTypeCost_USD(target.value);
    },
    [setTowerTypeCost_USD],
  );

  const moveFocus = useCallback(() => {
    const input = document.getElementById(towerTypeCost_USD_Id);
    if (!(input instanceof HTMLInputElement)) {
      throw Error(`Couldn't find #${towerTypeCost_USD_Id}`);
    }
    input.focus();
  }, [towerTypeCost_USD_Id]);

  return (
    <div className={styles.towerTypeContainer}>
      <h3 className={styles.towerTypeHeading}>
        <Text intlId="tower_type" />
      </h3>
      <p className={styles.towerTypeDescription}>
        <Text intlId="tower_type_desc" />
      </p>

      <div className={styles.towerTypeGrid}>
        <div>
          <label className={styles.towerTypeGridRow}>
            <span className={styles.labelWidth}>
              <Text intlId="tower_type" />
            </span>
            <select
              className={styles.towerTypeGridSelect}
              onChange={handleTowerTypeChange}
              value={towerTypeName}
            >
              <option value="" disabled>
                <Text intlId="sel" />
                {NBSP}
                <Text intlId="tower_type" />
              </option>
              {towerTypesDataFromDOM.map((towerTypeData) => (
                <option value={towerTypeData.value}>
                  <Text intlId={towerTypeData.element} />
                </option>
              ))}
            </select>
          </label>
        </div>
        <div>
          <label className={styles.towerTypeGridRow}>
            <span className={styles.labelWidth}>
              <Text intlId="cost" />
            </span>
            <div className={styles.towerTypeNumberAndUnitContainer}>
              <input
                id={towerTypeCost_USD_Id}
                name={towerTypeCost_USD_Id}
                type="number"
                className={styles.towerTypeCostInputNumber}
                onChange={handleCostChange}
                value={towerTypeCost_USD}
              />
              <span
                onClick={moveFocus}
                className={styles.towerTypeCostInputNumberUnit}
              >
                USD
              </span>
            </div>
          </label>
        </div>
      </div>
    </div>
  );
};

type RenderMidhaulAndBackhaulProps = {
  id: FormPath;
  modelPath: ModelPath;
  networkLocation: NetworkElement;
};

const RenderMidhaulAndBackhaul = ({
  id,
  modelPath,
  networkLocation,
}: RenderMidhaulAndBackhaulProps) => {
  const { useFormAndModel } = useStaticFormTsContext();
  const midhaulLinksId = `${id}.${
    'midhaulLink' satisfies keyof NetworkElement
  }` as FormPath;
  const midhaulLinksModelPath = `${modelPath}.${
    'midhaulLink' satisfies keyof NetworkElement
  }` as ModelPath;
  const [midhaulLinks, setMidhaulLinks] = useFormAndModel(
    midhaulLinksId,
    midhaulLinksModelPath,
    networkLocation.midhaulLink,
  );

  const handleAddNetworkLink = useCallback(() => {
    setMidhaulLinks((prevMidhaulLinks) => [
      ...prevMidhaulLinks,
      newBlankMidhaulLink(prevMidhaulLinks.length),
    ]);
  }, [setMidhaulLinks]);

  const backhaulLinksId = `${id}.${
    'backhaulLinks' satisfies keyof NetworkElement
  }` as FormPath;
  const backhaulLinksmModelPath = `${modelPath}.${
    'backhaulLinks' satisfies keyof NetworkElement
  }` as ModelPath;
  const [backhaulLinks, setBackhaulLinks] = useFormAndModel(
    backhaulLinksId,
    backhaulLinksmModelPath,
    networkLocation.backhaulLinks,
  );

  const handleAddBackhaulLink = useCallback(() => {
    setBackhaulLinks((prevBackhaulLinks) => [
      ...prevBackhaulLinks,
      newBlankBackhaulLink(prevBackhaulLinks.length),
    ]);
  }, [setBackhaulLinks]);

  return (
    <div className={styles.towerConnectContainer}>
      <h3 className={styles.towerConnectHeading}>
        <Text intlId="tower_connect" />
      </h3>
      <p className={styles.towerConnectDescription}>
        <Text intlId="tower_connect_desc" />
      </p>
      <h4 className={styles.towerConnectSmallHeading}>
        <Text intlId="net_links" />
      </h4>
      <p className={styles.towerConnectDescription}>
        <Text intlId="net_links_desc" />
      </p>

      {midhaulLinks.filter((item) => !item.isSoftDeleted).length > 0 && (
        <ol className={styles.networkLinksContainer}>
          {midhaulLinks
            .filter((networkLink) => !networkLink.isSoftDeleted)
            .map((networkLink) => {
              const newId = `${midhaulLinksId}.${networkLink.index}`;
              const newModelPath = `${midhaulLinksModelPath}.${networkLink.index}`;
              return (
                <li>
                  <RenderNetworkLink
                    key={networkLink.key}
                    id={newId}
                    networkLink={networkLink}
                    modelPath={newModelPath}
                  />
                </li>
              );
            })}
        </ol>
      )}
      <div className={styles.addNetworkLinkContainer}>
        <button
          type="button"
          onClick={handleAddNetworkLink}
          className={styles.addButton}
        >
          <Text intlId="add" />
          {NBSP}
          <Text intlId="net_link" />
        </button>
      </div>

      <h3 className={styles.towerConnectSmallHeading}>
        <Text intlId="backhaul_links" />
      </h3>
      <p className={styles.towerConnectDescription}>
        <Text intlId="backhaul_links_desc" />
      </p>

      {backhaulLinks.filter((item) => !item.isSoftDeleted).length > 0 && (
        <ol className={styles.backhaulLinksContainer}>
          {backhaulLinks
            .filter((item) => !item.isSoftDeleted)
            .map((backhaulLink) => {
              const newId =
                `${backhaulLinksId}.${backhaulLink.index}` as FormPath;
              const newModelPath =
                `${modelPath}.${backhaulLink.index}` as ModelPath;
              return (
                <li>
                  <RenderBackhaulLink
                    key={backhaulLink.key}
                    id={newId}
                    backhaulLink={backhaulLink}
                    modelPath={newModelPath}
                  />
                </li>
              );
            })}
        </ol>
      )}

      <div className={styles.addBackhaulLinkContainer}>
        <button
          type="button"
          onClick={handleAddBackhaulLink}
          className={styles.addButton}
        >
          <Text intlId="add" />
          {NBSP}
          <Text intlId="backhaul_link" />
        </button>
      </div>
    </div>
  );
};

type RenderNetworkLinkProps = {
  id: string;
  modelPath: string;
  networkLink: MidhaulLink;
};

const RenderNetworkLink = ({ id, modelPath }: RenderNetworkLinkProps) => {
  const { useFormAndModel } = useStaticFormTsContext();
  const typeId = `${id}.${'type' satisfies keyof MidhaulLink}` as FormPath;
  const typeModelPath = `${modelPath}.${
    'type' satisfies keyof MidhaulLink
  }` as ModelPath;
  const [typeValue, setTypeValue] = useFormAndModel(typeId, typeModelPath, '');
  const handleChangeType = useCallback(
    (e: ChangeEvent<HTMLSelectElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLSelectElement)) {
        throw Error('expected <select>');
      }
      setTypeValue(target.value);
    },
    [setTypeValue],
  );

  const isSoftDeletedId = `${id}.${
    'isSoftDeleted' satisfies keyof MidhaulLink
  }` as FormPath;
  const isSoftDeletedModelPath = `${modelPath}.${
    'isSoftDeleted' satisfies keyof MidhaulLink
  }` as ModelPath;
  const [, setIsSoftDeleted] = useFormAndModel(
    isSoftDeletedId,
    isSoftDeletedModelPath,
    false,
  );

  const handleDelete = useCallback(() => {
    setIsSoftDeleted(true);
  }, [setIsSoftDeleted]);

  return (
    <div className={styles.networkLinkContainer}>
      <select
        value={typeValue}
        onChange={handleChangeType}
        className={styles.networkLinkSelect}
      >
        <option value="" disabled>
          <Text intlId="sel" />
          {NBSP}
          <Text intlId="net_link" />
        </option>
        {midhaulDataFromDOM.map((item) => (
          <option value={item.name}>
            {item.name}
            {` - `}
            <Text intlId={item.element} />
          </option>
        ))}
      </select>
      <button
        onClick={handleDelete}
        aria-label="delete"
        className={styles.deleteNetworkLinkButton}
      >
        &times;
      </button>
    </div>
  );
};

type RenderBackhaulLinkProps = {
  id: FormPath;
  modelPath: ModelPath;
  backhaulLink: BackhaulLink;
};

const RenderBackhaulLink = ({
  id,
  modelPath,
  backhaulLink,
}: RenderBackhaulLinkProps) => {
  const { useFormAndModel } = useStaticFormTsContext();

  const monthlyChargeId = `${id}.${
    'monthlyCharge' satisfies keyof BackhaulLink
  }` as FormPath;
  const monthlyChargeModelPath = `${modelPath}.${
    'monthlyCharge' satisfies keyof BackhaulLink
  }` as ModelPath;
  const [montlyCharge, setMonthlyCharge] = useFormAndModel(
    monthlyChargeId,
    monthlyChargeModelPath,
    '0',
  );

  const trafficCost_USDId = `${id}.${
    'trafficCost_USD' satisfies keyof BackhaulLink
  }` as FormPath;
  const trafficCost_USD_modelPath = `${modelPath}.${
    'trafficCost_USD' satisfies keyof BackhaulLink
  }` as ModelPath;
  const [trafficCost_USD, setTrafficCost_USD] = useFormAndModel(
    trafficCost_USDId,
    trafficCost_USD_modelPath,
    '0',
  );

  const typeId = `${id}.${'type' satisfies keyof BackhaulLink}` as FormPath;
  const typeModelPath = `${modelPath}.${
    'type' satisfies keyof BackhaulLink
  }` as ModelPath;
  const [typeValue, setTypeValue] = useFormAndModel(
    typeId,
    typeModelPath,
    backhaulLink.type,
  );
  const handleChangeType = useCallback(
    (e: ChangeEvent<HTMLSelectElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLSelectElement)) {
        throw Error('expected <select>');
      }
      setTypeValue(target.value);

      const item = backhaulDataFromDOM.find(
        (item) => item.name === target.value,
      );
      if (item) {
        setMonthlyCharge(item.cost_base.toString());
        setTrafficCost_USD(item.cost_mbps.toString());
      }
    },
    [setTypeValue, setMonthlyCharge, setTrafficCost_USD],
  );

  const isSoftDeletedId = `${id}.${
    'isSoftDeleted' satisfies keyof MidhaulLink
  }` as FormPath;
  const isSoftDeletedModelPath = `${modelPath}.${
    'isSoftDeleted' satisfies keyof MidhaulLink
  }` as ModelPath;
  const [, setIsSoftDeleted] = useFormAndModel(
    isSoftDeletedId,
    isSoftDeletedModelPath,
    false,
  );

  const handleDelete = useCallback(() => {
    setIsSoftDeleted(true);
  }, [setIsSoftDeleted]);

  const handleChargeChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLInputElement)) {
        throw Error('expected <input>');
      }
      setMonthlyCharge(target.value);
    },
    [setMonthlyCharge],
  );

  const handleCostChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLInputElement)) {
        throw Error('expected <input>');
      }
      setTrafficCost_USD(target.value);
    },
    [setTrafficCost_USD],
  );

  return (
    <div className={styles.backhaulLinkContainer}>
      <select
        value={typeValue}
        onChange={handleChangeType}
        className={styles.backhaulLinkSelect}
      >
        <option value="" disabled>
          <Text intlId="sel" />
          {NBSP}
          <Text intlId="backhaul_link" />
        </option>
        {backhaulDataFromDOM.map((item) => (
          <option value={item.name}>
            {item.name}
            {` - `}
            <Text intlId={item.element} />
          </option>
        ))}
      </select>
      <div className={styles.backhaulItemContainer}>
        <label className={styles.backhaulItemLabel}>
          <Text intlId="fixed_monthly_charge" />
          <input
            id={monthlyChargeId}
            name={monthlyChargeId}
            type="number"
            value={montlyCharge}
            className={styles.backhaulItemNumberInput}
            onChange={handleChargeChange}
          />
        </label>
      </div>
      <div className={styles.backhaulItemContainer}>
        <label className={styles.backhaulItemLabel}>
          USD <Text intlId="cost_per_mbps" />
          <input
            id={trafficCost_USDId}
            name={trafficCost_USDId}
            type="number"
            value={trafficCost_USD}
            className={styles.backhaulItemNumberInput}
            onChange={handleCostChange}
          />
        </label>
      </div>
      <button
        onClick={handleDelete}
        aria-label="delete"
        className={styles.deleteBackhaulLinkButton}
      >
        &times;
      </button>
    </div>
  );
};

type ValidationErrorsProps = NodeProps<NetworkLocations>;

const ValidationErrors = ({ formPath, node }: ValidationErrorsProps) => {
  const { useFormAndModel } = useStaticFormTsContext();
  const locationsId = formPathJoin<NetworkLocations>(formPath, 'locations');
  const midhaulCountInputRef = useRef<HTMLInputElement>(null);
  const backhaulCountInputRef = useRef<HTMLInputElement>(null);

  const [networkLocations] = useFormAndModel(
    locationsId,
    node.modelPath as ModelPath,
    node.locations,
  );
  const midhaulCountId = `${locationsId}.midhaul`;
  const backhaulCountId = `${locationsId}.backhaul`;

  const networkLocationsCount = networkLocations.filter(
    (networkLocation) => !networkLocation.isSoftDeleted,
  ).length;

  const midhaulCount = networkLocations
    .filter((networkLocation) => !networkLocation.isSoftDeleted)
    .reduce((acc, networkLocation) => {
      return (
        acc +
        networkLocation.midhaulLink
          .filter((midhaulLink) => !midhaulLink.isSoftDeleted)
          .filter((backhaulLink) => backhaulLink.type).length
      );
    }, 0);

  const backhaulCount = networkLocations
    .filter((networkLocation) => !networkLocation.isSoftDeleted)
    .reduce((acc, networkLocation) => {
      return (
        acc +
        networkLocation.backhaulLinks
          .filter((backhaulLink) => !backhaulLink.isSoftDeleted)
          .filter((backhaulLink) => backhaulLink.type).length
      );
    }, 0);

  const backhaulNeededMessage = useIntlIdOrText(
    'alert_enter_backhaul',
    undefined,
  );

  const midhaulNeededMessage = useIntlIdOrText(
    'alert_enter_midhaul',
    undefined,
  );

  useEffect(() => {
    const { current: midhaulCountInput } = midhaulCountInputRef;
    if (
      !midhaulCountInput ||
      !(midhaulCountInput instanceof HTMLInputElement)
    ) {
      console.error(
        'Expected to find networkLocationsCountRef',
        midhaulCountInputRef,
      );
      return;
    }

    if (networkLocationsCount > 1 && midhaulCount < 2) {
      const errorText = midhaulNeededMessage ?? 'Field error';
      midhaulCountInput.setCustomValidity(errorText);
    } else {
      console.log('setting valid');
      midhaulCountInput.setCustomValidity(
        '', // setting empty string indicates to browser that it's valid
      );
    }
  }, [
    midhaulCountInputRef,
    midhaulCount,
    networkLocationsCount,
    midhaulNeededMessage,
  ]);

  useEffect(() => {
    const { current: backhaulCountInput } = backhaulCountInputRef;
    if (
      !backhaulCountInput ||
      !(backhaulCountInput instanceof HTMLInputElement)
    ) {
      console.error(
        'Expected to find networkLocationsCountRef',
        backhaulCountInputRef,
      );
      return;
    }

    if (backhaulCount < 1) {
      const errorText = backhaulNeededMessage ?? 'Field error';
      backhaulCountInput.setCustomValidity(errorText);
    } else {
      console.log('setting valid');
      backhaulCountInput.setCustomValidity(
        '', // setting empty string indicates to browser that it's valid
      );
    }
  }, [
    backhaulCountInputRef,
    backhaulCount,
    networkLocationsCount,
    backhaulNeededMessage,
  ]);

  return (
    <>
      <p className={styles.validationBlock}>
        Number of midhauls
        <input
          ref={midhaulCountInputRef}
          id={midhaulCountId}
          name={midhaulCountId}
          type="text"
          className={styles.countBox}
          value={midhaulCount}
        />
      </p>
      <p className={styles.validationBlock}>
        Number of backhauls
        <input
          ref={backhaulCountInputRef}
          id={backhaulCountId}
          name={backhaulCountId}
          type="text"
          className={styles.countBox}
          value={backhaulCount}
        />
      </p>
    </>
  );
};
