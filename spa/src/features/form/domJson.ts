export const getDomJson = (DOM_ID: string) => {
  if (typeof window === 'undefined') return;
  const jsonScriptElement = window.document.getElementById(DOM_ID);
  if (!jsonScriptElement) {
    throw Error(`Expected to find #${DOM_ID} <script> with data.`);
  }
  return JSON.parse(jsonScriptElement.innerHTML);
};
