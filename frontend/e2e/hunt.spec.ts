import {test,expect} from '@playwright/test';

test.beforeEach(async({page})=>{
  await page.route('**/api/health',route=>route.fulfill({json:{provider:'foundry',model:'witcher-mini',ready:true,access_required:true,detail:'Test fixture; no model calls.'}}));
});

test('desktop: clear activity, manager handoff, final decisions and optional evidence',async({page})=>{
  await page.setViewportSize({width:1440,height:1080});
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'The hunt, as it happens'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Start live hunt'})).toBeDisabled();
  await page.getByLabel('Test access key',{exact:true}).fill('fixture-only');
  await expect(page.getByRole('button',{name:'Start live hunt'})).toBeEnabled();
  await expect(page.getByLabel('Test access key',{exact:true})).toBeVisible();
  await expect(page.locator('.technical-details')).not.toHaveAttribute('open');
  await page.getByRole('button',{name:'Try a sample'}).click();
  await expect(page.getByRole('status')).toContainText('The Ringmaster is working',{timeout:5000});
  await expect(page.locator('.manager-card')).toHaveClass(/working/);
  await expect(page.getByRole('status')).toContainText('3 specialists are working in parallel',{timeout:20000});
  await expect(page.locator('.specialist-card.working')).toHaveCount(3);
  await expect(page.locator('.manager-message')).toContainText('Research assigned to all three specialists');
  await expect(page.locator('.manager-message')).toContainText('at the same time');
  await expect(page.locator('.specialist-card.blue .state-badge')).toContainText('WORKING NOW');
  await page.screenshot({path:'/private/tmp/witcher-simplified-active.png',fullPage:true});
  await expect(page.locator('.findings[open]')).toHaveCount(1,{timeout:16000});
  await expect(page.locator('.specialist-card.working')).toHaveCount(2);
  // Auto-open happens when the report arrives; readers can still collapse it.
  await page.locator('.findings>summary').first().click();
  await expect(page.locator('.findings[open]')).toHaveCount(0);
  await expect(page.getByRole('status')).toContainText('Your encounter plan is ready',{timeout:20000});
  await expect(page.locator('.findings')).toHaveCount(3);
  await expect(page.locator('.findings[open]')).toHaveCount(2);
  await expect(page.locator('.final-answer')).toContainText('Black Blood');
  await expect(page.locator('.working')).toHaveCount(0);
  await page.locator('.technical-details>summary').click();
  await expect(page.locator('.raw-events')).toBeVisible();
  await page.locator('.technical-details>summary').click();
  await page.screenshot({path:'/private/tmp/witcher-simplified-final.png',fullPage:true});
});

test('mobile: no horizontal overflow and stopping clears all working indicators',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await page.getByRole('button',{name:'Try a sample'}).click();
  await expect(page.getByRole('status')).toContainText('The Ringmaster is working',{timeout:5000});
  await expect(page.getByRole('button',{name:'Stop hunt'})).toBeVisible();
  const fits=await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth);
  expect(fits).toBe(true);
  await page.screenshot({path:'/private/tmp/witcher-simplified-mobile.png',fullPage:true});
  await page.getByRole('button',{name:'Stop hunt'}).click();
  await expect(page.getByRole('status')).toContainText('Hunt stopped');
  await expect(page.locator('.working')).toHaveCount(0);
});

test('failed live request gives a visible error without a stale working indicator',async({page})=>{
  await page.route('**/api/run',route=>route.fulfill({status:429,json:{error:'A hunt is already running. Try again shortly.'}}));
  await page.goto('/');
  await page.getByLabel('Test access key',{exact:true}).fill('fixture-only');
  await page.getByRole('button',{name:'Start live hunt'}).click();
  await expect(page.getByRole('alert')).toContainText('A hunt is already running');
  await expect(page.getByRole('status')).toContainText('The hunt was interrupted');
  await expect(page.locator('.working')).toHaveCount(0);
});
