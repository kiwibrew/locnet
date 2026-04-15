import {
  type Root,
  type MakeStaticFormTSValue,
  makeStaticFormTSValue,
} from '../form/node';
import type { ObjectPathDeep } from '../form/path';
import type { DefaultsDetail, ModelerAPIOutput } from './api-generated-client';
import type { ModelMapping } from './model';

type ApiError = {
  type: 'error';
  message: string;
};

export const locNetForm = {
  nodes: [
    {
      type: 'Disclosure',
      labelIntlId: 'introduction',
      children: [
        {
          type: 'HTML',
          intlId: 'welcome',
        },
      ],
    },
    {
      type: 'CountriesDropdown',
      labelIntlId: 'sel_country',
      modelPath: 'iso_3',
    },
    {
      type: 'Inert',
      children: [
        {
          type: 'Disclosure',
          labelIntlId: 'model_parameters',
          children: [
            {
              type: 'Disclosure',
              labelIntlId: 'community_characteristics',
              children: [
                {
                  type: 'CategoryTableForm',
                  columns: [
                    { type: 'TableFormColumnText', text: 'Variable' },
                    { type: 'TableFormColumnText', text: 'Value / Units' },
                    { type: 'TableFormColumnText', text: 'Explanation' },
                  ],
                  categories: ['community_cat', 'user_cat'],
                  labelToModelPathOverride: {} satisfies ModelMapping,
                },
              ],
            },
            {
              type: 'Disclosure',
              labelIntlId: 'sel_tech',
              children: [{ type: 'Technologies' }],
            },
            {
              type: 'Inert',
              children: [
                {
                  type: 'Disclosure',
                  labelIntlId: 'sel_freq',
                  children: [{ type: 'Frequencies' }],
                },
              ],
            },
            {
              type: 'Inert',
              children: [
                {
                  type: 'Disclosure',
                  labelIntlId: 'tech_paf',
                  children: [
                    {
                      type: 'CategoryTableForm',
                      columns: [
                        { type: 'TableFormColumnText', text: 'Variable' },
                        { type: 'TableFormColumnText', text: 'Value / Units' },
                        { type: 'TableFormColumnText', text: 'Explanation' },
                      ],
                      categories: ['paf_cat'],
                      labelToModelPathOverride: {} satisfies ModelMapping,
                    },
                  ],
                },
              ],
            },
            {
              type: 'Disclosure',
              labelIntlId: 'physical_characteristics',
              children: [
                { type: 'Terrain', modelPath: 'terrain_type' },
                { type: 'Vegetation', modelPath: 'vegetation_type' },
              ],
            },
            {
              type: 'Disclosure',
              labelIntlId: 'provider_type',
              children: [{ type: 'OrganisationType', modelPath: 'provider_type' }],
            },

            {
              type: 'Disclosure',
              labelIntlId: 'expert_opt',
              children: [
                {
                  type: 'CategoryTableForm',
                  columns: [
                    { type: 'TableFormColumnText', text: 'Variable' },
                    { type: 'TableFormColumnText', text: 'Value / Units' },
                    { type: 'TableFormColumnText', text: 'Explanation' },
                  ],
                  categories: [
                    'business_cat',
                    'general_cat',
                    'power_cat',
                  ],
                  labelToModelPathOverride: {} satisfies ModelMapping,
                },
              ],
            },
            {
              type: 'Disclosure',
              labelIntlId: 'net_elements',
              children: [
                {
                  type: 'NetworkElements',
                  modelPath: 'locations',
                  locations: [],
                },
              ],
            },
            { type: 'SubmitButton', labelIntlId: 'calculate_network' },
          ],
        },
      ],
    },
    {
      type: 'Loading',
    },
    {
      type: 'Disclosure',
      labelText: '',
      id: 'export',
      children: [
        {
          type: 'ExportFiles',
          selector: '#export',
          labelText: 'Report',
          labelPDFText: 'Download PDF',
          labelExcelText: 'Download Excel',
          labelCSVText: 'Download CSV',
        },
        {
          type: 'ExportTable',
          labelText: 'Summary of Outcomes',
          columnsFormPath: `api.modelerAPIOutput.${'outcomes_table_columns' satisfies keyof ModelerAPIOutput}`,
          rowsFormPath: `api.modelerAPIOutput.${'outcomes_table_rows' satisfies keyof ModelerAPIOutput}`,
          isSortable: true,
        },
        {
          type: 'ExportTable',
          labelText: 'Demand and CBA Assessment, Year 3 (2024 Dollars)',
          columnsFormPath: `api.modelerAPIOutput.${'dcba_table_columns' satisfies keyof ModelerAPIOutput}`,
          rowsFormPath: `api.modelerAPIOutput.${'dcba_table_rows' satisfies keyof ModelerAPIOutput}`,
          isSortable: true,
        },
        {
          type: 'ExportTable',
          labelText: 'Profit and Loss Statement (US $m)',
          columnsFormPath: `api.modelerAPIOutput.${'pl_table_columns' satisfies keyof ModelerAPIOutput}`,
          rowsFormPath: `api.modelerAPIOutput.${'pl_table_rows' satisfies keyof ModelerAPIOutput}`,
          isSortable: true,
          numberRounding: 4,
        },
        {
          type: 'ExportTable',
          labelText: 'Investment and Operating Cash Flow Statement ($m)',
          columnsFormPath: `api.modelerAPIOutput.${'inv_table_columns' satisfies keyof ModelerAPIOutput}`,
          rowsFormPath: `api.modelerAPIOutput.${'inv_table_rows' satisfies keyof ModelerAPIOutput}`,
          isSortable: true,
          numberRounding: 4,
        },
        {
          type: 'ExportScatterChart',
          labelText: 'Demand Curve',
          dataFormPath: `api.modelerAPIOutput.${'demand_curve_points' satisfies keyof ModelerAPIOutput}`,
        },
        {
          type: 'ExportTable',
          labelText: 'Network Details',
          columnsFormPath: `api.modelerAPIOutput.${'net_summary_table_columns' satisfies keyof ModelerAPIOutput}`,
          rowsFormPath: `api.modelerAPIOutput.${'net_summary_table_rows' satisfies keyof ModelerAPIOutput}`,
          isSortable: false,
        },
        {
          type: 'ExportDetailedResults',
          labelText: 'Network Elements',
          datasetFormPath: `api.modelerAPIOutput.${'detailed_results' satisfies keyof ModelerAPIOutput}`,
          isSortable: true,
        },
      ],
    },
  ],
  api: {
    characteristics: undefined as DefaultsDetail[] | ApiError | undefined,
    modelerAPIOutput: undefined as undefined | ModelerAPIOutput | ApiError,
  },
} as const satisfies Root;

export type LocNetForm = typeof locNetForm;

export type LocNetFormPath = ObjectPathDeep<LocNetForm>;

export type EditableLocNetForm = MakeStaticFormTSValue<LocNetForm>;

const locnetStaticFormValue = makeStaticFormTSValue(locNetForm);

// Set runtime default states below, so that (eg) isOpen=true aren't hardcoded into LocNet form schema TypeScript type.
locnetStaticFormValue.nodes[0].isButtonVisible = false;
locnetStaticFormValue.nodes[0].isOpen = true;
locnetStaticFormValue.nodes[2].children[0].isButtonVisible = false;
locnetStaticFormValue.nodes[2].isInert = true;
locnetStaticFormValue.nodes[2].children[0].children[2].isInert = true;
locnetStaticFormValue.nodes[4].isButtonVisible = false;

export { locnetStaticFormValue };
