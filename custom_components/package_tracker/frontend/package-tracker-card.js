function t(t,e,i,s){var r,o=arguments.length,n=o<3?e:null===s?s=Object.getOwnPropertyDescriptor(e,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(t,e,i,s);else for(var a=t.length-1;a>=0;a--)(r=t[a])&&(n=(o<3?r(n):o>3?r(e,i,n):r(e,i))||n);return o>3&&n&&Object.defineProperty(e,i,n),n}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e=globalThis,i=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),r=new WeakMap;let o=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(i&&void 0===t){const i=void 0!==e&&1===e.length;i&&(t=r.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&r.set(e,t))}return t}toString(){return this.cssText}};const n=(t,...e)=>{const i=1===t.length?t[0]:e.reduce((e,i,s)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+t[s+1],t[0]);return new o(i,t,s)},a=i?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const i of t.cssRules)e+=i.cssText;return(t=>new o("string"==typeof t?t:t+"",void 0,s))(e)})(t):t,{is:c,defineProperty:d,getOwnPropertyDescriptor:l,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,g=globalThis,_=g.trustedTypes,f=_?_.emptyScript:"",v=g.reactiveElementPolyfillSupport,m=(t,e)=>t,$={toAttribute(t,e){switch(e){case Boolean:t=t?f:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let i=t;switch(e){case Boolean:i=null!==t;break;case Number:i=null===t?null:Number(t);break;case Object:case Array:try{i=JSON.parse(t)}catch(t){i=null}}return i}},y=(t,e)=>!c(t,e),b={attribute:!0,type:String,converter:$,reflect:!1,useDefault:!1,hasChanged:y};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),g.litPropertyMetadata??=new WeakMap;let k=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=b){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(t,i,e);void 0!==s&&d(this.prototype,t,s)}}static getPropertyDescriptor(t,e,i){const{get:s,set:r}=l(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:s,set(e){const o=s?.call(this);r?.call(this,e),this.requestUpdate(t,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??b}static _$Ei(){if(this.hasOwnProperty(m("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(m("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(m("properties"))){const t=this.properties,e=[...h(t),...p(t)];for(const i of e)this.createProperty(i,t[i])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,i]of e)this.elementProperties.set(t,i)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const i=this._$Eu(t,e);void 0!==i&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const i=new Set(t.flat(1/0).reverse());for(const t of i)e.unshift(a(t))}else void 0!==t&&e.push(a(t));return e}static _$Eu(t,e){const i=e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,s)=>{if(i)t.adoptedStyleSheets=s.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const i of s){const s=document.createElement("style"),r=e.litNonce;void 0!==r&&s.setAttribute("nonce",r),s.textContent=i.cssText,t.appendChild(s)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){const i=this.constructor.elementProperties.get(t),s=this.constructor._$Eu(t,i);if(void 0!==s&&!0===i.reflect){const r=(void 0!==i.converter?.toAttribute?i.converter:$).toAttribute(e,i.type);this._$Em=t,null==r?this.removeAttribute(s):this.setAttribute(s,r),this._$Em=null}}_$AK(t,e){const i=this.constructor,s=i._$Eh.get(t);if(void 0!==s&&this._$Em!==s){const t=i.getPropertyOptions(s),r="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:$;this._$Em=s;const o=r.fromAttribute(e,t.type);this[s]=o??this._$Ej?.get(s)??o,this._$Em=null}}requestUpdate(t,e,i,s=!1,r){if(void 0!==t){const o=this.constructor;if(!1===s&&(r=this[t]),i??=o.getPropertyOptions(t),!((i.hasChanged??y)(r,e)||i.useDefault&&i.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,i))))return;this.C(t,e,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:s,wrapped:r},o){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),!0!==r||void 0!==o)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),!0===s&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,i]of t){const{wrapped:t}=i,s=this[e];!0!==t||this._$AL.has(e)||void 0===s||this.C(e,void 0,i,s)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};k.elementStyles=[],k.shadowRootOptions={mode:"open"},k[m("elementProperties")]=new Map,k[m("finalized")]=new Map,v?.({ReactiveElement:k}),(g.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const A=globalThis,x=t=>t,w=A.trustedTypes,E=w?w.createPolicy("lit-html",{createHTML:t=>t}):void 0,S="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,P="?"+C,U=`<${P}>`,O=document,T=()=>O.createComment(""),N=t=>null===t||"object"!=typeof t&&"function"!=typeof t,M=Array.isArray,H="[ \t\n\f\r]",z=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,R=/-->/g,j=/>/g,D=RegExp(`>|${H}(?:([^\\s"'>=/]+)(${H}*=${H}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),L=/'/g,I=/"/g,B=/^(?:script|style|textarea|title)$/i,q=(t=>(e,...i)=>({_$litType$:t,strings:e,values:i}))(1),W=Symbol.for("lit-noChange"),V=Symbol.for("lit-nothing"),F=new WeakMap,J=O.createTreeWalker(O,129);function K(t,e){if(!M(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==E?E.createHTML(e):e}const Z=(t,e)=>{const i=t.length-1,s=[];let r,o=2===e?"<svg>":3===e?"<math>":"",n=z;for(let e=0;e<i;e++){const i=t[e];let a,c,d=-1,l=0;for(;l<i.length&&(n.lastIndex=l,c=n.exec(i),null!==c);)l=n.lastIndex,n===z?"!--"===c[1]?n=R:void 0!==c[1]?n=j:void 0!==c[2]?(B.test(c[2])&&(r=RegExp("</"+c[2],"g")),n=D):void 0!==c[3]&&(n=D):n===D?">"===c[0]?(n=r??z,d=-1):void 0===c[1]?d=-2:(d=n.lastIndex-c[2].length,a=c[1],n=void 0===c[3]?D:'"'===c[3]?I:L):n===I||n===L?n=D:n===R||n===j?n=z:(n=D,r=void 0);const h=n===D&&t[e+1].startsWith("/>")?" ":"";o+=n===z?i+U:d>=0?(s.push(a),i.slice(0,d)+S+i.slice(d)+C+h):i+C+(-2===d?e:h)}return[K(t,o+(t[i]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),s]};class G{constructor({strings:t,_$litType$:e},i){let s;this.parts=[];let r=0,o=0;const n=t.length-1,a=this.parts,[c,d]=Z(t,e);if(this.el=G.createElement(c,i),J.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(s=J.nextNode())&&a.length<n;){if(1===s.nodeType){if(s.hasAttributes())for(const t of s.getAttributeNames())if(t.endsWith(S)){const e=d[o++],i=s.getAttribute(t).split(C),n=/([.?@])?(.*)/.exec(e);a.push({type:1,index:r,name:n[2],strings:i,ctor:"."===n[1]?et:"?"===n[1]?it:"@"===n[1]?st:tt}),s.removeAttribute(t)}else t.startsWith(C)&&(a.push({type:6,index:r}),s.removeAttribute(t));if(B.test(s.tagName)){const t=s.textContent.split(C),e=t.length-1;if(e>0){s.textContent=w?w.emptyScript:"";for(let i=0;i<e;i++)s.append(t[i],T()),J.nextNode(),a.push({type:2,index:++r});s.append(t[e],T())}}}else if(8===s.nodeType)if(s.data===P)a.push({type:2,index:r});else{let t=-1;for(;-1!==(t=s.data.indexOf(C,t+1));)a.push({type:7,index:r}),t+=C.length-1}r++}}static createElement(t,e){const i=O.createElement("template");return i.innerHTML=t,i}}function Q(t,e,i=t,s){if(e===W)return e;let r=void 0!==s?i._$Co?.[s]:i._$Cl;const o=N(e)?void 0:e._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),void 0===o?r=void 0:(r=new o(t),r._$AT(t,i,s)),void 0!==s?(i._$Co??=[])[s]=r:i._$Cl=r),void 0!==r&&(e=Q(t,r._$AS(t,e.values),r,s)),e}class X{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:i}=this._$AD,s=(t?.creationScope??O).importNode(e,!0);J.currentNode=s;let r=J.nextNode(),o=0,n=0,a=i[0];for(;void 0!==a;){if(o===a.index){let e;2===a.type?e=new Y(r,r.nextSibling,this,t):1===a.type?e=new a.ctor(r,a.name,a.strings,this,t):6===a.type&&(e=new rt(r,this,t)),this._$AV.push(e),a=i[++n]}o!==a?.index&&(r=J.nextNode(),o++)}return J.currentNode=O,s}p(t){let e=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}}class Y{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,s){this.type=2,this._$AH=V,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Q(this,t,e),N(t)?t===V||null==t||""===t?(this._$AH!==V&&this._$AR(),this._$AH=V):t!==this._$AH&&t!==W&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>M(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==V&&N(this._$AH)?this._$AA.nextSibling.data=t:this.T(O.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:i}=t,s="number"==typeof i?this._$AC(t):(void 0===i.el&&(i.el=G.createElement(K(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(e);else{const t=new X(s,this),i=t.u(this.options);t.p(e),this.T(i),this._$AH=t}}_$AC(t){let e=F.get(t.strings);return void 0===e&&F.set(t.strings,e=new G(t)),e}k(t){M(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let i,s=0;for(const r of t)s===e.length?e.push(i=new Y(this.O(T()),this.O(T()),this,this.options)):i=e[s],i._$AI(r),s++;s<e.length&&(this._$AR(i&&i._$AB.nextSibling,s),e.length=s)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=x(t).nextSibling;x(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,s,r){this.type=1,this._$AH=V,this._$AN=void 0,this.element=t,this.name=e,this._$AM=s,this.options=r,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=V}_$AI(t,e=this,i,s){const r=this.strings;let o=!1;if(void 0===r)t=Q(this,t,e,0),o=!N(t)||t!==this._$AH&&t!==W,o&&(this._$AH=t);else{const s=t;let n,a;for(t=r[0],n=0;n<r.length-1;n++)a=Q(this,s[i+n],e,n),a===W&&(a=this._$AH[n]),o||=!N(a)||a!==this._$AH[n],a===V?t=V:t!==V&&(t+=(a??"")+r[n+1]),this._$AH[n]=a}o&&!s&&this.j(t)}j(t){t===V?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===V?void 0:t}}class it extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==V)}}class st extends tt{constructor(t,e,i,s,r){super(t,e,i,s,r),this.type=5}_$AI(t,e=this){if((t=Q(this,t,e,0)??V)===W)return;const i=this._$AH,s=t===V&&i!==V||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,r=t!==V&&(i===V||s);s&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class rt{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){Q(this,t)}}const ot=A.litHtmlPolyfillSupport;ot?.(G,Y),(A.litHtmlVersions??=[]).push("3.3.2");const nt=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class at extends k{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,i)=>{const s=i?.renderBefore??e;let r=s._$litPart$;if(void 0===r){const t=i?.renderBefore??null;s._$litPart$=r=new Y(e.insertBefore(T(),t),t,void 0,i??{})}return r._$AI(t),r})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return W}}at._$litElement$=!0,at.finalized=!0,nt.litElementHydrateSupport?.({LitElement:at});const ct=nt.litElementPolyfillSupport;ct?.({LitElement:at}),(nt.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const dt=t=>(e,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},lt={attribute:!0,type:String,converter:$,reflect:!1,hasChanged:y},ht=(t=lt,e,i)=>{const{kind:s,metadata:r}=i;let o=globalThis.litPropertyMetadata.get(r);if(void 0===o&&globalThis.litPropertyMetadata.set(r,o=new Map),"setter"===s&&((t=Object.create(t)).wrapped=!0),o.set(i.name,t),"accessor"===s){const{name:s}=i;return{set(i){const r=e.get.call(this);e.set.call(this,i),this.requestUpdate(s,r,t,!0,i)},init(e){return void 0!==e&&this.C(s,void 0,t,e),e}}}if("setter"===s){const{name:s}=i;return function(i){const r=this[s];e.call(this,i),this.requestUpdate(s,r,t,!0,i)}}throw Error("Unsupported decorator location: "+s)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pt(t){return(e,i)=>"object"==typeof i?ht(t,e,i):((t,e,i)=>{const s=e.hasOwnProperty(i);return e.constructor.createProperty(i,t),s?Object.getOwnPropertyDescriptor(e,i):void 0})(t,e,i)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ut(t){return pt({...t,state:!0,attribute:!1})}const gt=n`
  :host {
    --pkg-delivered: #4caf50;
    --pkg-in-transit: #2196f3;
    --pkg-out-for-delivery: #ff9800;
    --pkg-pre-transit: #9e9e9e;
    --pkg-exception: #f44336;
    --pkg-unknown: #757575;
    --pkg-expired: #795548;
  }

  ha-card {
    padding: 16px;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 12px;
    font-size: 1.2em;
    font-weight: 500;
  }

  .package-count {
    font-size: 0.75em;
    color: var(--secondary-text-color);
  }

  .no-packages {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
  }

  .package-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .package-row {
    display: flex;
    align-items: center;
    padding: 12px;
    border-radius: 8px;
    background: var(--card-background-color, var(--ha-card-background));
    border: 1px solid var(--divider-color);
    gap: 12px;
  }

  .status-icon {
    flex-shrink: 0;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
  }

  .status-icon ha-icon {
    --mdc-icon-size: 22px;
  }

  .package-info {
    flex: 1;
    min-width: 0;
  }

  .package-label {
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .package-details {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.85em;
    color: var(--secondary-text-color);
    margin-top: 2px;
  }

  .carrier-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.75em;
    font-weight: 600;
    text-transform: uppercase;
    background: var(--primary-color);
    color: var(--text-primary-color);
  }

  .tracking-number {
    font-family: monospace;
    font-size: 0.85em;
  }

  .package-status {
    text-align: right;
    flex-shrink: 0;
  }

  .status-text {
    font-size: 0.85em;
    font-weight: 500;
    text-transform: capitalize;
  }

  .eta {
    font-size: 0.75em;
    color: var(--secondary-text-color);
    margin-top: 2px;
  }

  .tracking-link {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    color: var(--secondary-text-color);
    text-decoration: none;
    transition: background-color 0.2s, color 0.2s;
  }

  .tracking-link:hover {
    background-color: var(--divider-color);
    color: var(--primary-text-color);
  }

  .tracking-link ha-icon {
    --mdc-icon-size: 18px;
  }
`;let _t=class extends at{constructor(){super(...arguments),this._label="",this._trackingNumber="",this._carrier="",this._loading=!1,this._error="",this._success=!1}setConfig(t){this._config=t}getCardSize(){return 3}static getStubConfig(){return{type:"custom:package-tracker-add-card",title:"Add Package"}}static getConfigElement(){return document.createElement("package-tracker-add-card-editor")}render(){return this.hass&&this._config?q`
      <ha-card>
        <div class="card-header">${this._config.title??"Add Package"}</div>
        <div class="form">
          ${this._error?q`<div class="message error">${this._error}</div>`:V}
          ${this._success?q`<div class="message success">Package added successfully!</div>`:V}

          <div>
            <label>Label</label>
            <input
              type="text"
              .value="${this._label}"
              placeholder="e.g. Amazon Order"
              @input="${t=>this._label=t.target.value}"
            />
          </div>

          <div>
            <label>Tracking Number</label>
            <input
              type="text"
              .value="${this._trackingNumber}"
              placeholder="Carrier auto-detected"
              @input="${t=>this._trackingNumber=t.target.value}"
            />
          </div>

          <div>
            <label>Carrier (optional)</label>
            <select
              .value="${this._carrier}"
              @change="${t=>this._carrier=t.target.value}"
            >
              <option value="">Auto-detect</option>
              <option value="usps">USPS</option>
              <option value="ups">UPS</option>
              <option value="fedex">FedEx</option>
            </select>
          </div>

          <button @click="${this._submit}" ?disabled="${this._loading}">
            ${this._loading?"Adding…":"Add Package"}
          </button>
        </div>
      </ha-card>
    `:V}async _submit(){if(this._error="",this._success=!1,this._label.trim()&&this._trackingNumber.trim()){this._loading=!0;try{await this.hass.callService("package_tracker","add_package",{label:this._label.trim(),tracking_number:this._trackingNumber.trim(),...this._carrier?{carrier:this._carrier}:{}}),this._success=!0,this._label="",this._trackingNumber="",this._carrier=""}catch(t){this._error=t?.message??"Failed to add package. Check your tracking number."}finally{this._loading=!1}}else this._error="Label and tracking number are required."}};_t.styles=n`
    ha-card {
      padding: 16px;
    }

    .card-header {
      font-size: 1.2em;
      font-weight: 500;
      padding-bottom: 16px;
    }

    .form {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    label {
      font-size: 0.85em;
      color: var(--secondary-text-color);
      margin-bottom: 2px;
      display: block;
    }

    input,
    select {
      width: 100%;
      padding: 8px 10px;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      background: var(--card-background-color, var(--ha-card-background));
      color: var(--primary-text-color);
      font-size: 1em;
      box-sizing: border-box;
    }

    input:focus,
    select:focus {
      outline: none;
      border-color: var(--primary-color);
    }

    button {
      margin-top: 4px;
      padding: 10px;
      background: var(--primary-color);
      color: var(--text-primary-color);
      border: none;
      border-radius: 6px;
      font-size: 1em;
      cursor: pointer;
      transition: opacity 0.2s;
    }

    button:disabled {
      opacity: 0.6;
      cursor: default;
    }

    .message {
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 0.9em;
    }

    .message.error {
      background: rgba(244, 67, 54, 0.1);
      color: var(--error-color, #f44336);
    }

    .message.success {
      background: rgba(76, 175, 80, 0.1);
      color: #4caf50;
    }
  `,t([pt({attribute:!1})],_t.prototype,"hass",void 0),t([ut()],_t.prototype,"_config",void 0),t([ut()],_t.prototype,"_label",void 0),t([ut()],_t.prototype,"_trackingNumber",void 0),t([ut()],_t.prototype,"_carrier",void 0),t([ut()],_t.prototype,"_loading",void 0),t([ut()],_t.prototype,"_error",void 0),t([ut()],_t.prototype,"_success",void 0),_t=t([dt("package-tracker-add-card")],_t);let ft=class extends at{setConfig(t){this._config=t}render(){return this._config?q`
      <div style="padding:16px">
        <ha-textfield
          label="Title"
          .value=${this._config.title??"Add Package"}
          @input=${this._titleChanged}
          style="width:100%"
        ></ha-textfield>
      </div>
    `:V}_titleChanged(t){this._config&&this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:{...this._config,title:t.target.value}},bubbles:!0,composed:!0}))}};t([pt({attribute:!1})],ft.prototype,"hass",void 0),t([ut()],ft.prototype,"_config",void 0),ft=t([dt("package-tracker-add-card-editor")],ft),window.customCards=window.customCards||[],window.customCards.push({type:"package-tracker-add-card",name:"Package Tracker — Add Package",description:"Form card to add a new package to track"});const vt={delivered:"mdi:package-variant-closed-check",in_transit:"mdi:truck-delivery",out_for_delivery:"mdi:truck-fast",pre_transit:"mdi:package-variant",exception:"mdi:alert-circle",expired:"mdi:clock-alert",unknown:"mdi:help-circle"},mt={delivered:"var(--pkg-delivered)",in_transit:"var(--pkg-in-transit)",out_for_delivery:"var(--pkg-out-for-delivery)",pre_transit:"var(--pkg-pre-transit)",exception:"var(--pkg-exception)",expired:"var(--pkg-expired)",unknown:"var(--pkg-unknown)"},$t={delivered:"Delivered",in_transit:"In Transit",out_for_delivery:"Out for Delivery",pre_transit:"Pre-Transit",exception:"Exception",expired:"Expired",unknown:"Unknown"};let yt=class extends at{setConfig(t){this._config={show_delivered:!0,...t}}getCardSize(){return 3}static getConfigElement(){return document.createElement("package-tracker-card-editor")}static getStubConfig(){return{type:"custom:package-tracker-card",title:"Package Tracker",show_delivered:!0}}render(){if(!this.hass||!this._config)return V;const t=this._getPackages(),e=this._config.title??"Package Tracker";return q`
      <ha-card>
        <div class="card-header">
          <span>${e}</span>
          <span class="package-count">${t.length} package${1!==t.length?"s":""}</span>
        </div>
        ${0===t.length?q`<div class="no-packages">No packages being tracked</div>`:q`<div class="package-list">${t.map(t=>this._renderPackage(t))}</div>`}
      </ha-card>
    `}_getPackages(){let t=Object.keys(this.hass.states).filter(t=>{if(!t.startsWith("sensor."))return!1;const e=this.hass.states[t].attributes;return void 0!==e.tracking_number&&void 0!==e.carrier}).map(t=>{const e=this.hass.states[t];return{entityId:t,state:e.state,attributes:e.attributes}});this._config?.show_delivered||(t=t.filter(t=>"delivered"!==t.state));const e={out_for_delivery:0,exception:1,in_transit:2,pre_transit:3,unknown:4,expired:5,delivered:6};return t.sort((t,i)=>{const s=e[t.state]??4,r=e[i.state]??4;if(s!==r)return s-r;return(t.attributes.estimated_delivery?new Date(t.attributes.estimated_delivery).getTime():1/0)-(i.attributes.estimated_delivery?new Date(i.attributes.estimated_delivery).getTime():1/0)}),t}_renderPackage(t){const e=t.state||"unknown",i=vt[e]||vt.unknown,s=mt[e]||mt.unknown,r=$t[e]||e,o=t.attributes;let n="";if(o.estimated_delivery)try{n=new Date(o.estimated_delivery).toLocaleDateString(void 0,{month:"short",day:"numeric"})}catch{}return q`
      <div class="package-row">
        <div class="status-icon" style="background-color: ${s}">
          <ha-icon icon="${i}"></ha-icon>
        </div>
        <div class="package-info">
          <div class="package-label">${o.label||"Package"}</div>
          <div class="package-details">
            <span class="carrier-badge">${o.carrier||""}</span>
            <span class="tracking-number">${o.tracking_number||""}</span>
          </div>
        </div>
        <div class="package-status">
          <div class="status-text" style="color: ${s}">${r}</div>
          ${n?q`<div class="eta">ETA: ${n}</div>`:V}
        </div>
        ${o.tracking_url?q`<a
              class="tracking-link"
              href="${o.tracking_url}"
              target="_blank"
              rel="noopener noreferrer"
              title="View on carrier website"
              @click="${t=>t.stopPropagation()}"
            >
              <ha-icon icon="mdi:open-in-new"></ha-icon>
            </a>`:V}
      </div>
    `}};yt.styles=gt,t([pt({attribute:!1})],yt.prototype,"hass",void 0),t([ut()],yt.prototype,"_config",void 0),yt=t([dt("package-tracker-card")],yt),window.customCards=window.customCards||[],window.customCards.push({type:"package-tracker-card",name:"Package Tracker Card",description:"Track your shipping packages from USPS, UPS, and FedEx"});export{yt as PackageTrackerCard};
