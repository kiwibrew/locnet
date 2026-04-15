import { useCallback, useState } from 'react';

export const useBoolean = () => {
  const [bool, setBool] = useState<boolean>(false);
  const setFalse = useCallback(() => setBool(false), [setBool]);
  const setTrue = useCallback(() => setBool(true), [setBool]);
  const setToggle = useCallback(() => setBool((bool) => !bool), [setBool]);

  return {
    state: bool,
    setTrue,
    setFalse,
    setToggle,
  };
};
