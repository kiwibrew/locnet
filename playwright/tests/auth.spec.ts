import { expect, test } from '@playwright/test';

import { signIn } from './fixtures';


test('protects the application and rejects invalid credentials', async ({ page }) => {
  await page.goto('/app');
  await expect(page).toHaveURL(/\/$/);

  await page.getByLabel('Email').fill('user-e2e@example.com');
  await page.getByLabel('Password').fill('incorrect-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('alert')).toContainText(
    'Invalid email, password, or account status',
  );
});


test('signs in, opens protected API documentation, and signs out', async ({
  page,
}) => {
  await signIn(page);
  await expect(page.getByRole('link', { name: 'Manage users' })).toHaveCount(0);
  const signOut = page.getByRole('button', { name: /Sign out/ });
  await expect(signOut).toHaveCSS('border-style', 'solid');
  await expect(signOut).toHaveCSS('background-color', 'rgb(255, 255, 255)');
  await page.goto('/docs');
  await expect(page).toHaveTitle(/Community Network Builder API/);

  await page.goto('/app');
  await page.getByRole('button', { name: /Sign out/ }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto('/app');
  await expect(page).toHaveURL(/\/$/);
});


test('administrator can create a user and enable API access', async ({ page }) => {
  await signIn(
    page,
    process.env.E2E_ADMIN_EMAIL ?? 'admin-e2e@example.com',
    process.env.E2E_ADMIN_PASSWORD ?? 'admin-password',
  );
  await expect(page.getByRole('link', { name: 'Manage users' })).toBeVisible();
  await page.goto('/manage-users');

  const email = `playwright-${Date.now()}@example.com`;
  await page.getByLabel('Email').last().fill(email);
  await page.getByLabel('Password').last().fill('playwright-password');
  await page.getByRole('button', { name: 'Create user' }).click();
  await expect(page).toHaveURL(/\/manage-users$/);

  const row = page.getByRole('row').filter({ hasText: email });
  await row.getByRole('button', { name: 'Enable API' }).click();
  await expect(page.getByRole('heading', { name: `API token for ${email}` })).toBeVisible();
  await expect(page.getByLabel('API token')).not.toHaveValue('');
});
