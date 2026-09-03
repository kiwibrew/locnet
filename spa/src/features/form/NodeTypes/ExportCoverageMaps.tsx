import { Map as MapLibreMap } from 'maplibre-gl';
import type { GeoJSON } from 'geojson';
import { useEffect, useState } from 'react';
import { z } from 'zod';
import type { LocationCoverageMap } from '../../locnet/api-generated-client';
import { FormNodeSchema } from '../base';
import { useStaticFormTsContext, type FormPath } from '../FormProvider';
import type { NodeProps } from '../node';
import { getGeoJsonBounds } from './ExportCoverageMaps.utils';
import { getMapStyleUrl } from './mapLibre';
import styles from './ExportCoverageMaps.module.css';

export const ExportCoverageMapsSchema = FormNodeSchema.extend({
  type: z.literal('ExportCoverageMaps'),
  coverageMapsFormPath: z.string(),
});

export type ExportCoverageMaps = z.infer<typeof ExportCoverageMapsSchema>;

type Props = NodeProps<ExportCoverageMaps>;
type MapStatus = 'loading' | 'ready' | 'unavailable';

const emptyCoverageMaps: LocationCoverageMap[] = [];

const isGeoJson = (value: object): value is GeoJSON =>
  'type' in value && typeof value.type === 'string';

type CoverageMapProps = {
  coverageMap: LocationCoverageMap;
  index: number;
};

const CoverageMap = ({ coverageMap, index }: CoverageMapProps) => {
  const [snapshotDataUrl, setSnapshotDataUrl] = useState<string>();
  const [status, setStatus] = useState<MapStatus>('loading');
  const [mapContainer, setMapContainer] = useState<HTMLDivElement | null>(null);
  const geojson = isGeoJson(coverageMap.geojson)
    ? coverageMap.geojson
    : undefined;

  useEffect(() => {
    if (!mapContainer || !geojson) {
      if (mapContainer) setStatus('unavailable');
      return;
    }

    let cancelled = false;
    let map: MapLibreMap | undefined;
    const sourceId = `result-coverage-${index}`;
    const statusTimeout = window.setTimeout(() => {
      if (!cancelled) setStatus('unavailable');
    }, 10_000);

    getMapStyleUrl()
      .then((styleUrl) => {
        if (cancelled) return;
        try {
          map = new MapLibreMap({
            container: mapContainer,
            style: styleUrl,
            center: [coverageMap.longitude, coverageMap.latitude],
            zoom: 10,
            canvasContextAttributes: { preserveDrawingBuffer: true },
          });
        } catch (error) {
          console.error('Failed to initialise coverage map', error);
          setStatus('unavailable');
          return;
        }

        map.on('load', () => {
          if (!map || cancelled) return;
          map.once('idle', () => {
            if (!map || cancelled) return;
            try {
              const dataUrl = map.getCanvas().toDataURL('image/png');
              if (!dataUrl || dataUrl === 'data:,') {
                setStatus('unavailable');
                return;
              }
              setSnapshotDataUrl(dataUrl);
              setStatus('ready');
              window.clearTimeout(statusTimeout);
            } catch (error) {
              // Cross-origin tile servers can make a WebGL canvas unreadable.
              // Keep the interactive map available even if PDF capture fails.
              console.error('Unable to capture coverage map for PDF', error);
              setStatus('unavailable');
            }
          });
          map.addSource(sourceId, { type: 'geojson', data: geojson });
          map.addLayer({
            id: sourceId,
            type: 'fill',
            source: sourceId,
            paint: {
              'fill-color': '#2196f3',
              'fill-opacity': 0.3,
              'fill-outline-color': '#1976d2',
            },
          });

          const bounds = getGeoJsonBounds(geojson, coverageMap.longitude);
          if (bounds) {
            map.fitBounds(bounds, {
              animate: false,
              maxZoom: 15,
              padding: 40,
            });
          }

        });
      })
      .catch((error) => {
        console.error('Failed to load coverage map style', error);
        if (!cancelled) setStatus('unavailable');
      });

    return () => {
      cancelled = true;
      window.clearTimeout(statusTimeout);
      map?.remove();
    };
  }, [coverageMap.latitude, coverageMap.longitude, geojson, index, mapContainer]);

  return (
    <article
      className={styles.mapCard}
      data-pdf-map-status={status}
      data-testid={`coverage-map-${index}`}
    >
      <h4 className={styles.mapHeading}>{coverageMap.location_name}</h4>
      <div
        ref={setMapContainer}
        className={styles.interactiveMap}
        aria-label={`Coverage map for ${coverageMap.location_name}`}
      />
      {snapshotDataUrl ? (
        <img
          className={styles.pdfMap}
          src={snapshotDataUrl}
          alt={`Coverage map for ${coverageMap.location_name}`}
        />
      ) : (
        <p className={styles.pdfFallback}>
          Map image unavailable for {coverageMap.location_name}.
        </p>
      )}
    </article>
  );
};

export const RenderExportCoverageMaps = ({ node }: Props) => {
  const { useWatchFormStore } = useStaticFormTsContext();
  const coverageMaps = useWatchFormStore(
    node.coverageMapsFormPath as FormPath,
    emptyCoverageMaps,
  );

  if (coverageMaps.length === 0) return null;

  return (
    <section className={styles.container} data-testid="coverage-maps">
      <h3 className={styles.labelText}>{node.labelText}</h3>
      <div className={styles.mapGrid}>
        {coverageMaps.map((coverageMap, index) => (
          <CoverageMap
            coverageMap={coverageMap}
            index={index}
            key={`${coverageMap.location_name}-${index}`}
          />
        ))}
      </div>
    </section>
  );
};
