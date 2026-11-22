const {chromium,expect}=require('@playwright/test');
(async()=>{const b=await chromium.launch({args:['--no-sandbox']});try{
const ctx=await b.newContext(), host=await ctx.newPage(), display=await ctx.newPage();
let live={steps:[{kind:'presentation',title:'Deck'},{kind:'quiz',title:'Quiz'}],title:'Event',view:'step',cursor:0,page_count:3,page:0,revision:1}, calls=[];
await ctx.route(/\/events\/(one\/live|display\/program\/.*)/,async route=>{
const req=route.request();if(req.url().includes('/program/page/'))return route.fulfill({body:'<svg xmlns="http://www.w3.org/2000/svg"/>',contentType:'image/svg+xml'});
if(req.method()==='PUT'){const {action}=req.postDataJSON();calls.push(action);live.page+=action==='next_page'?1:-1;live.revision++;}
await route.fulfill({json:req.url().includes('/program/state')?live:{live,display_key:'key'}});
});
await host.goto('http://localhost:4209/probe.html');await display.goto('http://localhost:4209/probe.html?display');await host.bringToFront();
const wait=(p,n)=>expect(p.getByText('Slayt '+n+' / 3',{exact:true})).toBeVisible();
await wait(host,1);await host.keyboard.press('ArrowLeft');await host.keyboard.down('PageDown');await wait(host,2);await host.keyboard.down('PageDown');await host.keyboard.up('PageDown');await wait(display,2);
await host.keyboard.press('ArrowRight');await wait(host,3);await host.keyboard.press('PageDown');await wait(display,3);await host.keyboard.press('PageUp');await wait(host,2);await host.keyboard.press('ArrowLeft');await wait(host,1);
live.steps[0].slide_seconds=5;await host.reload();await wait(host,1);await host.keyboard.press('ArrowRight');await host.waitForTimeout(250);expect(calls).toEqual(['next_page','next_page','previous_page','previous_page']);console.log('PASS two-window synchronization, four keys, hold, boundaries, automatic mode');}finally{await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
