import { setWorkerUrl } from 'maplibre-gl';
import mapLibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';

// MapLibre resolves its worker relative to the application bundle, but Vite
// does not discover that runtime-generated URL. Importing the worker as a Vite
// worker entry emits it (and its dependencies) and gives MapLibre a valid URL.
setWorkerUrl(mapLibreWorkerUrl);

// The style URL is provided by the backend (see /api/map_config) so the tile
// provider and its API key stay server-side. Cache the lookup for the session.
let mapStyleUrlPromise: Promise<string> | undefined;

export const getMapStyleUrl = (): Promise<string> => {
  if (!mapStyleUrlPromise) {
    mapStyleUrlPromise = fetch('/api/map_config')
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Map configuration returned HTTP ${response.status}`);
        }
        return response.json();
      })
      .then((body: { style_url: string }) => body.style_url);
  }
  return mapStyleUrlPromise;
};
