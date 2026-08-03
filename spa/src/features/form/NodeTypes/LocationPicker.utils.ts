type LongitudeBounds = {
  getWest: () => number;
  getEast: () => number;
};

const FULL_WORLD_LONGITUDE_DEGREES = 360;

/**
 * MapLibre wraps max-bound longitudes into a single world. A viewport that is
 * one or more worlds wide would therefore fold into an unrelated, narrower
 * longitude range when used as maxBounds.
 */
export const canUseViewportAsMaxBounds = (
  bounds: LongitudeBounds,
): boolean => {
  const longitudeSpan = bounds.getEast() - bounds.getWest();
  return (
    Number.isFinite(longitudeSpan) &&
    longitudeSpan > 0 &&
    longitudeSpan < FULL_WORLD_LONGITUDE_DEGREES
  );
};
