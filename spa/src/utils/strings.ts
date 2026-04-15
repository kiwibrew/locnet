export const NBSP = '\u00A0'

export const replaceNonNumberChars = (input: string): string => input.replace(/[^0-9.]/g, '')