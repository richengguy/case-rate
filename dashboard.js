(()=>{"use strict";const e=Chart;class t{constructor(e){this._values=e}get upperInterval(){return this._values[0]}get lowerInterval(){return this._values[1]}}class n{constructor(e){var n;this._interpolated=e.interpolated,this._raw=null!==(n=e.raw)&&void 0!==n?n:[],this._confidence=[],null!=e.confidenceInterval&&(this._confidence=e.confidenceInterval.map((e=>new t(e))))}get interpolated(){return this._interpolated}get raw(){return this._raw}get confidenceIntervals(){return this._confidence}get hasRaw(){return 0!=this._raw.length}get hasConfidenceIntervals(){return 0!=this._confidence.length}}class r{constructor(e){this._dates=e.date,this._length=e.date.length,this._samples={};for(const t of e.timeseries)this._samples[t.name]=new n(t)}get length(){return this._length}get dates(){return this._dates}get series(){return this._samples}static FetchUrlAsync(e){return t=this,n=void 0,s=function*(){var t=yield fetch(e),n=yield t.json();return new r(n)},new((i=void 0)||(i=Promise))((function(e,r){function o(e){try{c(s.next(e))}catch(e){r(e)}}function a(e){try{c(s.throw(e))}catch(e){r(e)}}function c(t){var n;t.done?e(t.value):(n=t.value,n instanceof i?n:new i((function(e){e(n)}))).then(o,a)}c((s=s.apply(t,n||[])).next())}));var t,n,i,s}}var i=function(e,t,n,r){return new(n||(n=Promise))((function(i,s){function o(e){try{c(r.next(e))}catch(e){s(e)}}function a(e){try{c(r.throw(e))}catch(e){s(e)}}function c(e){var t;e.done?i(e.value):(t=e.value,t instanceof n?t:new n((function(e){e(t)}))).then(o,a)}c((r=r.apply(e,t||[])).next())}))};class s{constructor(e,t){this._name=e,this._url=t}get name(){return this._name}get url(){return this._url}}class o{constructor(e,t,n){this._base=e,this._date=t,this._source=new s(n.description,n.url);var r=n.name,i=r.indexOf(":");i<0?(this._country=r,this._region=null):(this._country=r.substring(0,i),this._region=r.substring(i+1))}get country(){return this._country}get region(){return this._region}get source(){return this._source}FetchTimeSeriesAsync(){return i(this,void 0,void 0,(function*(){let e;e=null==this._region?`${this._country}.json`:`${this._country}_${this._region}.json`;let t=`${this._base}/${e}?t=${this._date.getTime()}`;return yield r.FetchUrlAsync(t)}))}}class a{constructor(e,t,n){this._config=n,this._generated=e,this._regions=t}entryDetails(e){return this._regions[e]}entryDetailsByName(e,t){for(const n of this._regions){let r=e===n.country,i=t===n.region;if(r&&i)return n}return null}listSubnationalRegions(e){let t=[];for(const n of this._regions)null!==n.region&&n.country===e&&t.push(n.region);return t}get configuration(){return this._config}get generatedOn(){return this._generated}get numberOfEntries(){return this._regions.length}static LoadAsync(e){return i(this,void 0,void 0,(function*(){const t=(new Date).getTime(),n=yield fetch(`${e}/analysis.json?t=${t}`),r=yield n.json(),i=new Date(r.generated);return new a(i,r.regions.map((t=>new o(e,i,t))),r.config)}))}}const c="#244A57";function l(e,t){return null==t?e:e.slice(-t)}function u(e,t){return{type:"bar",label:"Reported",data:l(e.raw,t),backgroundColor:"#C0D6DD",barPercentage:1,categoryPercentage:1}}function h(e,t){return{type:"line",label:"LOESS Filtered",data:l(e.interpolated,t),backgroundColor:c,borderColor:c,fill:!1,pointRadius:0,borderWidth:1.5,cubicInterpolationMode:void 0}}function d(t,n,r,i){let s=[h(n,i),u(n,i)];r=l(r,i),new e(t,{type:"line",data:{labels:r,datasets:s},options:{maintainAspectRatio:!1,scales:{yAxes:[{ticks:{min:0},scaleLabel:{display:!0,labelString:"Cases"}}]}}})}function g(e,t,n){let r=e.querySelector(`.${t}`);const i=n.length;r.textContent=n[i-1].toLocaleString()}class f{constructor(e,t,n){this._index=e,this._container=n,this._dailyChange=t.series.dailyChange,this._dates=function(e){let t=function(e){let t=function(e){return new URL(document.location.href).searchParams.get(e)}(e);if(null==t)return null;let n=parseInt(t);return isNaN(n)?null:n}("pastDays");return l(e.dates,t)}(t)}get container(){return this._container}get dailyChange(){return this._dailyChange}get dates(){return this._dates}get index(){return this._index}}class y{constructor(e){this._template=e}RenderAsync(e,t){return n=this,r=void 0,s=function*(){let n=this._template.content.cloneNode(!0);n.querySelector(".country-name").textContent=t.country;let r=yield t.FetchTimeSeriesAsync();return g(n,"new-cases",r.series.dailyChange.raw),g(n,"total-confirmed",r.series.cases.raw),function(e,t,n){let r=e.querySelector(".relative-growth");const i=100*(n[n.length-1]-1);r.textContent=`${i.toLocaleString()} %`}(n,0,r.series.growthFactor.interpolated),function(e,t){let n=e.querySelector(".details-link");null===t.region?n.href=`details.html?country=${t.country}&pastDays=90`:n.href=`details.html?country=${t.country}&region=${t.region}&pastDays=90`}(n,t),n.querySelector(".daily-cases-chart").id=`cases-${e}`,new f(e,r,n)},new((i=void 0)||(i=Promise))((function(e,t){function o(e){try{c(s.next(e))}catch(e){t(e)}}function a(e){try{c(s.throw(e))}catch(e){t(e)}}function c(t){var n;t.done?e(t.value):(n=t.value,n instanceof i?n:new i((function(e){e(n)}))).then(o,a)}c((s=s.apply(n,r||[])).next())}));var n,r,i,s}}window.onload=()=>{let t=document.getElementById("dashboard"),n=document.getElementById("date-generated"),r=document.getElementById("__template");e.defaults.global.legend.onClick=()=>{};let i=new y(r);a.LoadAsync("_analysis").then((e=>{n.innerText=e.generatedOn.toDateString();let t=[];for(let n=0;n<e.numberOfEntries;n++){let r=e.entryDetails(n);null===r.region&&t.push(i.RenderAsync(n,r))}return Promise.all(t)})).then((e=>{for(const n of e)t.appendChild(n.container);return e})).then((e=>{for(const t of e)d(document.getElementById(`cases-${t.index}`),t.dailyChange,t.dates,90)}))}})();