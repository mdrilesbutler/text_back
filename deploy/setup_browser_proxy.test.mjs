import assert from 'node:assert/strict';
import {test} from 'node:test';
import {patchKeyboardBundle, BUGGY_KEY_CODE} from './setup_browser_proxy.mjs';

test('forwards browser virtual key codes instead of character codes', () => {
  const source = `e=>{let r;let ${BUGGY_KEY_CODE};return i}`;
  const keyCode = Function(`return (${patchKeyboardBundle(source)})`)();
  for (const [key, code] of [['.',190], ['@',50], ['-',189], ['_',189],
    ['/',191], [':',186], ['a',65], ['p',80], ['Delete',46]]) {
    assert.equal(keyCode({key, keyCode:code}), code);
  }
});

test('refuses an unknown or ambiguous upstream bundle', () => {
  assert.throws(() => patchKeyboardBundle('different bundle'));
  assert.throws(() => patchKeyboardBundle(BUGGY_KEY_CODE.repeat(2)));
});
