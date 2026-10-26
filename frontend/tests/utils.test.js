import test from 'node:test';
import assert from 'node:assert/strict';
import {number,signed,linePath,query,shiftDate,dateLabel,timeLabel} from '../src/utils.js';
test('missing values remain missing, not zero',()=>{assert.equal(number(null),'—');assert.equal(number(0),'0');});
test('signed error direction is explicit',()=>{assert.equal(signed(15),'+15');assert.equal(signed(-15),'-15');});
test('chart breaks across missing intervals',()=>{assert.equal(linePath([{v:1},{v:null},{v:3}],'v',x=>x,y=>y),'M0.00,1.00  M2.00,3.00');});
test('January boundary advances to February',()=>{assert.equal(shiftDate('2026-01-31',1),'2026-02-01');});
test('query encoding preserves the cutoff',()=>{assert.equal(query({cutoff:'09:00',missing:undefined}),'cutoff=09%3A00');});
test('time formatting is London, not browser local time',()=>{assert.equal(timeLabel('2026-01-02T00:00:00Z'),'00:00');assert.equal(timeLabel('2026-07-02T00:00:00Z'),'01:00');});
