import { describe, expect, test } from 'vitest';
import { canUseViewportAsMaxBounds } from './LocationPicker.utils';

const longitudeBounds = (west: number, east: number) => ({
  getWest: () => west,
  getEast: () => east,
});

describe('canUseViewportAsMaxBounds', () => {
  test('accepts a viewport narrower than one world', () => {
    expect(canUseViewportAsMaxBounds(longitudeBounds(-120, 120))).toBe(true);
  });

  test.each([
    ['Canada', -671.6110937293979, 477.9889225723946],
    ['Argentina', -387.0653763763076, 259.8310848713071],
    ['exactly one world', -180, 180],
  ])('rejects the %s viewport', (_name, west, east) => {
    expect(canUseViewportAsMaxBounds(longitudeBounds(west, east))).toBe(false);
  });
});
