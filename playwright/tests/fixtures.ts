import { expect, test as base, type Page } from '@playwright/test';


export const signIn = async (
  page: Page,
  email = process.env.E2E_USER_EMAIL ?? 'user-e2e@example.com',
  password = process.env.E2E_USER_PASSWORD ?? 'user-password',
) => {
  await page.goto('/');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/app$/);
};


export const test = base.extend({
  page: async ({ page }, use) => {
    await signIn(page);
    await use(page);
  },
});

export { expect };
