// JSON parser with duplicate-key, depth, size and prototype-key rejection.
export function safeParse(text){
 if(typeof text!=='string'||text.length>15000000)throw Error('JSON 超过15MB或类型错误');
 let at=0;const bad=new Set(['__proto__','prototype','constructor']);
 const fail=()=>{throw Error('JSON格式、重复键或深度不安全；原数据未变')};
 const ws=()=>{while(/\s/.test(text[at]||'')&&at<text.length)at++};
 const string=()=>{const begin=at++;while(at<text.length){const ch=text[at++];if(ch==='"'){try{return JSON.parse(text.slice(begin,at))}catch{fail()}}if(ch==='\\')at++;else if(ch.charCodeAt(0)<32)fail()}fail()};
 function value(depth){if(depth>64)fail();ws();const ch=text[at];
  if(ch==='"')return string();
  if(ch==='{'){at++;ws();const o=Object.create(null),keys=new Set;if(text[at]==='}'){at++;return o}while(true){ws();if(text[at]!=='"')fail();const k=string();if(keys.has(k)||bad.has(k))fail();keys.add(k);ws();if(text[at++]!==':')fail();o[k]=value(depth+1);ws();const c=text[at++];if(c==='}')return o;if(c!==',')fail()}}
  if(ch==='['){at++;ws();const a=[];if(text[at]===']'){at++;return a}while(true){if(a.length>=5000)fail();a.push(value(depth+1));ws();const c=text[at++];if(c===']')return a;if(c!==',')fail()}}
  for(const [s,v]of [['true',true],['false',false],['null',null]])if(text.slice(at,at+s.length)===s){at+=s.length;return v}
  const m=/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(text.slice(at));if(!m)fail();at+=m[0].length;const n=Number(m[0]);if(!Number.isFinite(n)||Math.abs(n)>Number.MAX_SAFE_INTEGER)fail();return n;
 }
 const result=value(0);ws();if(at!==text.length)fail();return result;
}
