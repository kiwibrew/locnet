import { assertNever } from '../../utils/typescript';
import { type NodeProps, type Node } from './node';
import { RenderCategoryTableForm } from './NodeTypes/CategoryTableForm';
import { RenderCountriesDropdown } from './NodeTypes/CountriesDropdown';
import { RenderDisclosure } from './NodeTypes/Disclosure';
import { RenderExportScatterChart } from './NodeTypes/ExportScatterChart';
import { RenderExportTable } from './NodeTypes/ExportTable';
import { RenderExportDetailedResults } from './NodeTypes/ExportDetailedResults';
import { RenderFieldHelp } from './NodeTypes/FieldHelp';
import { RenderFrequencies } from './NodeTypes/Frequencies';
import { RenderHTML } from './NodeTypes/Html';
import { RenderInert } from './NodeTypes/Inert';
import { RenderLoading } from './NodeTypes/Loading';
import { RenderNetworkElements } from './NodeTypes/NetworkElements';
import { RenderOrganisationType } from './NodeTypes/OrganisationType';
import { RenderRadioToggleButtons } from './NodeTypes/RadioToggleButtons';
import { RenderSelect } from './NodeTypes/Select';
import { RenderSubmitButton } from './NodeTypes/SubmitButton';
import {
  RenderTableForm,
  RenderTableFormColumnText,
  RenderTableFormRowHeader,
  RenderTableFormRowCells,
  RenderTableFormCellText,
  RenderTableFormCellInputNumber,
  RenderTableFormCellInputText,
} from './NodeTypes/TableForm';
import { RenderTechnologies } from './NodeTypes/Technologies';
import { RenderTerrain } from './NodeTypes/Terrain';
import { RenderText } from './NodeTypes/Text';
import { RenderToggleButton } from './NodeTypes/ToggleButton';
import { RenderVegetation } from './NodeTypes/Vegetation';
import { RenderDataTable } from './NodeTypes/DataTable';
import { RenderObjectTable } from './NodeTypes/ObjectTable';
import { RenderExportFiles } from './NodeTypes/ExportFiles';

type Props = NodeProps<Node>;

export const RenderNode = (props: Props) => {
  const { node, formPath } = props;

  switch (node.type) {
    case 'Text':
      return <RenderText node={node} formPath={formPath} />;
    case 'HTML':
      return <RenderHTML node={node} formPath={formPath} />;
    case 'Inert':
      return <RenderInert node={node} formPath={formPath} />;
    case 'Disclosure':
      return <RenderDisclosure node={node} formPath={formPath} />;
    case 'CountriesDropdown':
      return <RenderCountriesDropdown node={node} formPath={formPath} />;
    case 'CategoryTableForm':
      return <RenderCategoryTableForm node={node} formPath={formPath} />;
    case 'TableForm':
      return <RenderTableForm node={node} formPath={formPath} />;
    case 'SubmitButton':
      return <RenderSubmitButton node={node} formPath={formPath} />;
    case 'TableFormColumnText':
      return <RenderTableFormColumnText node={node} formPath={formPath} />;
    case 'TableFormRowHeader':
      return <RenderTableFormRowHeader node={node} formPath={formPath} />;
    case 'TableFormRowCells':
      return <RenderTableFormRowCells node={node} formPath={formPath} />;
    case 'TableFormCellText':
      return <RenderTableFormCellText node={node} formPath={formPath} />;
    case 'TableFormCellInputText':
      return <RenderTableFormCellInputText node={node} formPath={formPath} />;
    case 'TableFormCellInputNumber':
      return <RenderTableFormCellInputNumber node={node} formPath={formPath} />;
    case 'Technologies':
      return <RenderTechnologies node={node} formPath={formPath} />;
    case 'Frequencies':
      return <RenderFrequencies node={node} formPath={formPath} />;
    case 'ToggleButton':
      return <RenderToggleButton node={node} formPath={formPath} />;
    case 'Terrain':
      return <RenderTerrain node={node} formPath={formPath} />;
    case 'Vegetation':
      return <RenderVegetation node={node} formPath={formPath} />;
    case 'Select':
      return <RenderSelect node={node} formPath={formPath} />;
    case 'FieldHelp':
      return <RenderFieldHelp node={node} formPath={formPath} />;
    case 'RadioToggleButtons':
      return <RenderRadioToggleButtons node={node} formPath={formPath} />;
    case 'OrganisationType':
      return <RenderOrganisationType node={node} formPath={formPath} />;
    case 'NetworkElements':
      return <RenderNetworkElements node={node} formPath={formPath} />;
    case 'Loading':
      return <RenderLoading node={node} formPath={formPath} />;
    case 'DataTable':
      return <RenderDataTable node={node} formPath={formPath} />;
    case 'ExportTable':
      return <RenderExportTable node={node} formPath={formPath} />;
    case 'ExportDetailedResults':
      return <RenderExportDetailedResults node={node} formPath={formPath} />;
    case 'ExportScatterChart':
      return <RenderExportScatterChart node={node} formPath={formPath} />;
    case 'ObjectTable':
      return <RenderObjectTable node={node} formPath={formPath} />;
    case 'ExportFiles':
      return <RenderExportFiles node={node} formPath={formPath} />;
  }

  assertNever(node);
};
