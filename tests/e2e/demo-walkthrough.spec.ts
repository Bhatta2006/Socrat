import { expect, test, type Page } from '@playwright/test';
import path from 'node:path';
import { mkdir } from 'node:fs/promises';

const forbidden = /unavailable|waitlist|under review|pending|not released|coming soon|lorem|TODO/i;
const shots = path.resolve('docs/demo/screens');

async function inspect(page: Page, name: string, project: string) {
  await expect(page.getByText('Demo build — sample content, local sandbox. Not reviewed for release.', { exact: true })).toBeVisible();
  await expect(page.locator('body')).not.toContainText(forbidden);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
  await mkdir(shots, { recursive: true });
  await page.evaluate(() => window.scrollTo(0,0));
  await page.screenshot({ path: path.join(shots, `${project}-${name}.png`), fullPage: true, animations: 'disabled' });
}

async function edit(page: Page, code: string) {
  const editor = page.getByRole('textbox', { name: 'Solution source code', exact: true });
  await editor.click();
  await page.keyboard.press('ControlOrMeta+A');
  await page.keyboard.insertText(code);
}

function solution(language: string, statement: string): string {
  // These are presenter-written solutions to the visible problem, not API
  // solutions, hidden tests, fixture state, or synthetic worker responses.
  let py = 'return sum(a)', cpp = 'return accumulate(a.begin(),a.end(),0LL);', java = 'long r=0; for(long x:a)r+=x; return r;';
  const text = statement.toLowerCase();
  if (text.includes('adjacent pairs with unequal')) { py='return sum(a[i]!=a[i-1] for i in range(1,len(a)))'; cpp='long long r=0;for(int i=1;i<(int)a.size();i++)r+=a[i]!=a[i-1];return r;'; java='long r=0;for(int i=1;i<a.length;i++)if(a[i]!=a[i-1])r++;return r;'; }
  else if(text.includes('absolute differences')) {py='return sum(abs(a[i]-a[i-1]) for i in range(1,len(a)))';cpp='long long r=0;for(int i=1;i<(int)a.size();i++)r+=abs(a[i]-a[i-1]);return r;';java='long r=0;for(int i=1;i<a.length;i++)r+=Math.abs(a[i]-a[i-1]);return r;';}
  else if(text.includes('last minus first')) {py='return a[-1]-a[0] if a else 0';cpp='return a.empty()?0:a.back()-a.front();';java='return a.length==0?0:a[a.length-1]-a[0];';}
  else if(text.includes('one-based position')) {py='return sum((i+1)*x for i,x in enumerate(a))';cpp='long long r=0;for(int i=0;i<(int)a.size();i++)r+=(i+1)*a[i];return r;';java='long r=0;for(int i=0;i<a.length;i++)r+=(i+1)*a[i];return r;';}
  else if(text.includes('even zero-based')) {py='return sum(x if i%2==0 else -x for i,x in enumerate(a))';cpp='long long r=0;for(int i=0;i<(int)a.size();i++)r+=(i%2==0?a[i]:-a[i]);return r;';java='long r=0;for(int i=0;i<a.length;i++)r+=(i%2==0?a[i]:-a[i]);return r;';}
  else if(text.includes('sum of strictly positive')) {py='return sum(x for x in a if x>0)';cpp='long long r=0;for(auto x:a)if(x>0)r+=x;return r;';java='long r=0;for(long x:a)if(x>0)r+=x;return r;';}
  else if(text.includes('first positive')) {py='return next((i for i,x in enumerate(a) if x>0),-1)';cpp='for(int i=0;i<(int)a.size();i++)if(a[i]>0)return i;return -1;';java='for(int i=0;i<a.length;i++)if(a[i]>0)return i;return -1;';}
  else if(text.includes("last zero")) {py='return next((i for i in range(len(a)-1,-1,-1) if a[i]==0),-1)';cpp='for(int i=(int)a.size()-1;i>=0;i--)if(a[i]==0)return i;return -1;';java='for(int i=a.length-1;i>=0;i--)if(a[i]==0)return i;return -1;';}
  else if(text.includes('later reading is larger')) {py='return sum(a[i]>a[i-1] for i in range(1,len(a)))';cpp='long long r=0;for(int i=1;i<(int)a.size();i++)r+=a[i]>a[i-1];return r;';java='long r=0;for(int i=1;i<a.length;i++)if(a[i]>a[i-1])r++;return r;';}
  else if(text.includes('equal to zero')) {py='return a.count(0)';cpp='return count(a.begin(),a.end(),0);';java='long r=0;for(long x:a)if(x==0)r++;return r;';}
  else if(text.includes('negative')) {py='return sum(x<0 for x in a)';cpp='return count_if(a.begin(),a.end(),[](long long x){return x<0;});';java='long r=0;for(long x:a)if(x<0)r++;return r;';}
  else if (text.includes('positive')) { py = 'return sum(x>0 for x in a)'; cpp = 'return count_if(a.begin(),a.end(),[](long long x){return x>0;});'; java = 'long r=0;for(long x:a)if(x>0)r++;return r;'; }
  else if (text.includes('even')) { py = 'return sum(x%2==0 for x in a)'; cpp = 'return count_if(a.begin(),a.end(),[](long long x){return x%2==0;});'; java = 'long r=0;for(long x:a)if(x%2==0)r++;return r;'; }
  else if (text.includes('maximum') || text.includes('largest')) { py = 'return max(a,default=0)'; cpp = 'return a.empty()?0:*max_element(a.begin(),a.end());'; java = 'if(a.length==0)return 0;long r=a[0];for(long x:a)r=Math.max(r,x);return r;'; }
  else if (text.includes('minimum') || text.includes('smallest')) { py = 'return min(a,default=0)'; cpp = 'return a.empty()?0:*min_element(a.begin(),a.end());'; java = 'if(a.length==0)return 0;long r=a[0];for(long x:a)r=Math.min(r,x);return r;'; }
  else if (text.includes('length') || text.includes('how many values')) { py = 'return len(a)'; cpp = 'return a.size();'; java = 'return a.length;'; }
  if (language === 'python') return `def solve(a):\n    ${py}\nimport sys\nd=list(map(int,sys.stdin.read().split()));print(solve(d[1:1+d[0]]))\n`;
  if (language === 'cpp') return `#include <bits/stdc++.h>\nusing namespace std;\nlong long solve(vector<long long>a){${cpp}}\nint main(){int n;cin>>n;vector<long long>a(n);for(auto&x:a)cin>>x;cout<<solve(a)<<'\\n';}\n`;
  return `import java.util.*;\npublic class Solution {static long solve(long[]a){${java}}public static void main(String[]args){Scanner s=new Scanner(System.in);int n=s.nextInt();long[]a=new long[n];for(int i=0;i<n;i++)a[i]=s.nextLong();System.out.println(solve(a));}}\n`;
}

async function completeAssessment(page: Page, kind: string, answer: string) {
  await page.getByRole('button', { name: `Start ${kind} check`, exact: true }).click();
  await page.getByLabel('Your response', { exact: true }).fill(answer);
  await page.getByRole('button', { name: 'Submit response', exact: true }).click();
  await page.getByRole('button', { name: 'Finish assessment', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'independently assessed' })).toBeVisible();
}

for (const language of ['python', 'cpp', 'java']) {
  test(`fresh ${language} learner completes real practice, checks, recovery, export and deletion`, async ({ page }, info) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
    await page.goto('/');
    await inspect(page, `${language}-landing`, info.project.name);
    await page.getByRole('link', { name: 'Find your starting point' }).click();
    await inspect(page, `${language}-login`, info.project.name);
    await page.getByRole('button', { name: 'Start fresh as a new learner' }).click();
    await page.getByLabel('Display name').fill(`Demo ${language}`);
    await page.getByLabel('I confirm I am 18 or older.').check();
    await page.getByRole('button', { name: 'Save profile', exact: true }).click();
    await page.getByRole('button', { name: 'Continue to your learning goal' }).click();
    await page.getByLabel('Programming language', { exact: true }).selectOption(language);
    await page.getByRole('button', { name: 'Next', exact: true }).click();
    await page.getByRole('button', { name: 'Next', exact: true }).click();
    await page.getByLabel('I have no fixed target date.').check();
    await page.getByLabel('Days each week').selectOption('6');
    await inspect(page, `${language}-onboarding`, info.project.name);
    await page.getByRole('button', { name: 'Review goal', exact: true }).click();
    await page.getByLabel('I reviewed this goal and starting route.').check();
    await page.getByRole('button', { name: 'Confirm goal', exact: true }).click();
    await page.getByRole('link', { name: /diagnostic/i }).last().click();
    await page.getByRole('button', { name: 'Start diagnostic', exact: true }).click();
    for (let i = 0; i < 16; i++) {
      if (await page.getByRole('button', { name: 'View diagnostic evidence' }).isVisible()) break;
      await page.getByRole('radio').first().check();
      const [saved] = await Promise.all([page.waitForResponse(r => r.url().endsWith('/responses') && r.request().method()==='POST', {timeout:30000}), page.getByRole('button', { name: 'Save answer and continue' }).click()]);
      const next = await saved.json();
      if (!next.item) break;
      await expect(page.getByText(`${next.answered} answers saved. Item ${next.item.position}.`, {exact:true})).toBeVisible();
    }
    await page.getByRole('button', { name: 'View diagnostic evidence' }).click();
    await inspect(page, `${language}-diagnostic`, info.project.name);
    await page.getByRole('link', { name: /plan/i }).last().click();
    await page.getByRole('button', { name: /Generate|Create.*plan/ }).click();
    await page.getByRole('button', { name: 'Confirm reviewed plan', exact: true }).click();
    await inspect(page, `${language}-plan`, info.project.name);
    await page.getByRole('link', { name: 'Assessments', exact:true }).click();
    await completeAssessment(page, 'baseline', '4');
    await page.getByRole('link', { name: 'Plan', exact:true }).click();
    await page.getByRole('button', { name:'Refresh plan', exact:true }).click();
    await page.getByRole('button', { name:'Confirm reviewed plan', exact:true }).click();
    await page.getByRole('link', { name: /Today/ }).last().click();
    await inspect(page, `${language}-today`, info.project.name);
    await page.getByRole('link', { name: /Start today’s session/ }).click();
    await page.getByRole('button', { name: 'Start today’s session', exact: true }).click();
    await expect(page).toHaveURL(/\/session\/(?!today)[^/]+$/);
    // Retrieval → explanation → guided trace; these save participation, not mastery.
    await page.getByLabel('Your response', { exact: true }).fill('5');
    await page.getByRole('button', { name: 'Save and continue' }).click();
    await expect(page.getByRole('heading',{level:4}).filter({hasText:'instruction:'})).toBeVisible();
    await page.getByRole('button', { name: 'Save and continue' }).click();
    await expect(page.getByRole('heading',{level:4}).filter({hasText:'guided:'})).toBeVisible();
    await page.getByLabel('Your response', { exact: true }).fill('Initialize the accumulator, visit each input, then print its final value.');
    await page.getByRole('button', { name: 'Save and continue' }).click();
    await page.getByRole('button', { name: 'Open code editor' }).click();
    const statement = await page.locator('.coding-problem').innerText();
    await edit(page, language === 'python' ? 'def solve(:' : 'this is invalid source');
    await page.getByRole('button', { name: 'Run samples', exact: true }).click();
    await expect(page.getByText(/Case 1: (compile|runtime) error/)).toBeVisible({ timeout: 120_000 });
    await expect(page.getByRole('region',{name:'Problems'})).toContainText(/line 1/);
    await inspect(page, `${language}-compiler-error`, info.project.name);
    await edit(page, solution(language, statement));
    await page.getByRole('button', { name: 'Run samples', exact: true }).click();
    await expect(page.getByText('Case 1: passed', { exact: false })).toBeVisible({ timeout: 120_000 });
    await page.getByLabel('Your plan and what you tried').fill('I traced the sample and checked the empty input. I want help checking my invariant.');
    await page.getByRole('button', { name: 'Ask for a hint', exact: true }).click();
    await expect(page.getByText(/Hint level 1/)).toBeVisible();
    await page.getByLabel('Your plan and what you tried').fill('I checked the empty sequence. After each visit my count represents unequal adjacent pairs seen so far; the first value starts no pair.');
    await page.getByRole('button', { name: 'Ask for a hint', exact: true }).click();
    await expect(page.getByText(/Hint level 2/)).toBeVisible();
    await expect(page.getByText(/Solution locked during independent practice/)).toBeVisible();
    await inspect(page, `${language}-session-editor`, info.project.name);
    await page.getByRole('button', { name: 'Submit assisted attempt', exact: true }).click();
    await expect(page.getByText(/Case 20: passed/)).toBeVisible({ timeout: 240_000 });
    await page.getByRole('button', { name: 'Continue after Submit' }).click();
    await page.getByLabel('Your response', { exact: true }).fill('3');
    await page.getByRole('button', { name: 'Save and continue' }).click();
    await page.getByRole('link', { name: 'See your learning evidence' }).click();
    await expect(page.getByText('assisted (level 2)', { exact: false })).toBeVisible();
    await inspect(page, `${language}-progress`, info.project.name);
    await page.getByRole('link', { name: 'Assessments', exact: true }).click();
    await inspect(page, `${language}-assessments`, info.project.name);
    await page.getByRole('link', { name: 'Demo controls', exact: true }).click();
    await page.getByRole('button', { name: 'Move to weekly check' }).click();
    await expect(page.getByRole('button', { name: 'Move to weekly check' })).toBeEnabled();
    await inspect(page, `${language}-demo`, info.project.name);
    await page.getByRole('link', { name: 'View assessments' }).click();
    await completeAssessment(page, 'weekly', '7');
    await page.getByRole('link', { name: 'Demo controls', exact: true }).click();
    await page.getByRole('button', { name: 'Move to retention check' }).click();
    await page.getByRole('link', { name: 'View assessments' }).click();
    await expect(page.getByRole('status').filter({ hasText: /[1-9].*concepts due for retention/ })).toBeVisible();
    await completeAssessment(page, 'retention', '6');
    await page.getByRole('link', { name: 'Demo controls', exact: true }).click();
    await page.getByRole('button', { name: 'Simulate missed days' }).click();
    await page.getByRole('link', { name: 'Review recovery' }).click();
    await page.getByRole('button', { name: /Recover|Recalculate/ }).click();
    await page.getByRole('button', { name: 'Confirm reviewed plan', exact: true }).click();
    await page.getByRole('link', { name: 'Settings', exact: true }).click();
    await page.getByText('Your data and privacy controls', { exact: true }).click();
    await inspect(page, `${language}-settings`, info.project.name);
    const downloaded = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Export my learning data' }).click();
    expect((await downloaded).suggestedFilename()).toBe('socrat-learning-data.json');
    await page.getByLabel('Type DELETE MY DATA to request deletion').fill('DELETE MY DATA');
    await page.getByRole('button', { name: 'Request account deletion' }).click();
    await expect(page.getByRole('heading', { name: 'Your deletion request' })).toBeVisible();
    await inspect(page, `${language}-deletion`, info.project.name);
    expect(errors).toEqual([]);
  });
}
