
"use strict";

const CP = {
  1:{name:"Ancient Ruins of Akshank",clue:"Ancient ruins of Akshank",pos:[22.681686603215834,75.87866723631592]},
  2:{name:"Seasonal Island View",clue:"View of a seasonal island",pos:[22.681073904231067,75.878925999408]},
  3:{name:"Cricket Ground",clue:"Let's play cricket",pos:[22.68041805437934,75.88003275723203]},
  4:{name:"C-Shaped Building",clue:"'C' shaped building",pos:[22.681496434563755,75.88100346491773]},
  5:{name:"Vishesh Jupiter Corner",clue:"Closest corner to Vishesh Jupiter Hospital",pos:[22.682554447540795,75.88115789942242]}
};

const PH = {
  WAITING_FOR_CHECKPOINT_3:["PROLOGUE / 01","Find the first trace.","Visit the location described by your first clue."],
  FIND_WAND_AND_BROOM:["CHAPTER I / 02","The seven-minute warning.","Collect the broom and wand before the Death Eaters arrive."],
  FIND_SHIELD_AND_ARTIFACTS:["CHAPTER II / 03","The final protection.","Recover the ancient spell and the protective relics before time runs out."],
  WON:["EPILOGUE","The wards hold.","IET-DAVV is safe."],
  GAME_OVER:["THE FALL","Time has run out.","The campus could not be protected."]
};

const $ = id => document.getElementById(id);

const s = {
  id:null,
  state:null,
  map:null,
  markers:{},
  radii:{},
  player:null,
  accuracy:null,
  watch:null,
  requestBusy:false,
  dialogQueue:[],
  dialogOpen:false,
  deadline:null,
  poll:null,
  tick:null,
  locationTs:0,
  endscreen:false
};

const escapeHtml = t => String(t).replace(
  /[&<>"']/g,
  c => ({
    '&':'&amp;',
    '<':'&lt;',
    '>':'&gt;',
    '"':'&quot;',
    "'":'&#39;'
  }[c])
);

async function request(path,options={}){
  const res=await fetch(path,{
    headers:{'Content-Type':'application/json'},
    ...options
  });

  const json=await res.json().catch(()=>({}));
  if(!res.ok)throw Error(json.error||`HTTP ${res.status}`);
  return json;
}

function notice(text){
  $('notice').textContent=text;
  clearTimeout(notice.timer);
  notice.timer=setTimeout(()=>$('notice').textContent='',5800);
}

function show(screen){
  for(const id of ['welcome','play','ending'])
    $(id).hidden=(id!==screen);

  if(screen==='play'&&s.map)
    setTimeout(()=>s.map.invalidateSize(),80);
}

// ======================================
// MAP
// ======================================

function newMap(){
  if(s.map)return;

  s.map=L.map('map',{zoomControl:false})
    .setView([22.6815,75.88],17);

  L.control.zoom({
    position:'bottomright'
  }).addTo(s.map);

  L.tileLayer(
    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    {
      maxZoom:20,
      attribution:'© OpenStreetMap contributors'
    }
  ).addTo(s.map);
}

function markerIcon(n,done){
  return L.divIcon({
    className:'',
    html:`<div class="pin ${done?'done':''}">${done?'✓':n}</div>`,
    iconSize:[33,33],
    iconAnchor:[16,16]
  });
}

// ======================================
// ONE-TIME HINT SYSTEM
// ======================================

function hintKey(){
  return `quest_hint_${s.id}`;
}

function getHintedCheckpoint(){
  if(!s.id)return null;

  const value=localStorage.getItem(hintKey());

  if(value===null)return null;

  const id=Number(value);
  return CP[id]?id:null;
}

function hintAlreadyUsed(){
  return s.id!==null &&
    localStorage.getItem(hintKey())!==null;
}

function revealHint(checkpointId){
  if(!s.id||!s.state)return;

  if(hintAlreadyUsed()){
    notice('You have already used your only location hint.');
    return;
  }

  const active=(s.state.checkpoints||[])
    .some(c=>Number(c.id)===checkpointId);

  const reached=(s.state.reached_checkpoints||[])
    .includes(checkpointId);

  if(!active||reached){
    notice('This checkpoint is not available for a hint.');
    return;
  }

  const confirmed=confirm(
    `Reveal the location of Checkpoint ${checkpointId}?\n\n`+
    'You can use only ONE location hint during this quest.'
  );

  if(!confirmed)return;

  localStorage.setItem(
    hintKey(),
    String(checkpointId)
  );

  // Update only map and clue controls.
  // Do not call render() again because that
  // could replay previously received dialogues.
  renderMap(s.state);
  renderClues(s.state);

  // Move map camera to the revealed checkpoint.
  if(s.map){
    s.map.setView(
      CP[checkpointId].pos,
      18
    );
  }

  notice('Location hint revealed. No hints remaining.');
}

// ======================================
// CHECKPOINT MAP VISIBILITY
// ======================================

function renderMap(st){
  if(!s.map)return;

  const active=new Set(
    (st.checkpoints||[]).map(c=>Number(c.id))
  );

  const reached=new Set(
    st.reached_checkpoints||[]
  );

  const hintedId=getHintedCheckpoint();

  for(let i=1;i<=5;i++){

    // A checkpoint appears ONLY when:
    // 1. The hint was used on it.
    // 2. It is currently active.
    // 3. It has not yet been completed.

    const visible=(
      hintedId===i &&
      active.has(i) &&
      !reached.has(i)
    );

    if(!visible){

      if(s.markers[i]){
        s.map.removeLayer(s.markers[i]);
        delete s.markers[i];
      }

      if(s.radii[i]){
        s.map.removeLayer(s.radii[i]);
        delete s.radii[i];
      }

      continue;
    }

    const cp=CP[i];

    if(!s.markers[i]){
      s.markers[i]=L.marker(cp.pos)
        .addTo(s.map);
    }

    s.markers[i].setIcon(
      markerIcon(i,false)
    );

    s.markers[i].bindPopup(
      `<b>Checkpoint ${i}</b><p>${escapeHtml(cp.clue)}</p>`
    );

    const radius=25+
      (st.boosts?.[i]?.extra_radius_m||0);

    if(!s.radii[i]){
      s.radii[i]=L.circle(cp.pos,{
        radius,
        color:'#ba9356',
        weight:1,
        fillOpacity:.07
      }).addTo(s.map);
    }

    s.radii[i].setRadius(radius);
    s.radii[i].setStyle({
      color:'#ba9356'
    });
  }
}

// ======================================
// CLUE DISPLAY
// ======================================

function renderClues(st){
  const reached=new Set(
    st.reached_checkpoints||[]
  );

  const hintUsed=hintAlreadyUsed();

  const available=(st.checkpoints||[])
    .filter(c=>!reached.has(Number(c.id)));

  $('clues').innerHTML=available.map(c=>{

    const id=Number(c.id);

    return `
      <div class="clue">
        <p>✦ ${escapeHtml(c.clue)}</p>

        <button
          type="button"
          class="location-hint-button"
          data-checkpoint="${id}"
          ${hintUsed?'disabled':''}
          style="
            margin-top:12px;
            padding:10px 14px;
            border:1px solid #c9a65e;
            border-radius:8px;
            background:${hintUsed?'#302b38':'#c9a65e'};
            color:${hintUsed?'#aaa':'#151018'};
            font-size:12px;
            font-weight:bold;
            cursor:${hintUsed?'not-allowed':'pointer'};
            width:100%;
          "
        >
          ${
            hintUsed
              ?'✦ HINT ALREADY USED'
              :'✧ REVEAL LOCATION HINT (1 USE)'
          }
        </button>
      </div>
    `;

  }).join('')||
    '<p class="clue">All objectives complete.</p>';

  // Connect buttons after rendering them.
  $('clues')
    .querySelectorAll('.location-hint-button:not(:disabled)')
    .forEach(button=>{

      button.addEventListener('click',()=>{
        revealHint(
          Number(button.dataset.checkpoint)
        );
      });

    });
}

// ======================================
// MAIN GAME RENDERING
// ======================================

function render(st){
  s.state=st;

  const info=PH[st.phase]||
    PH.WAITING_FOR_CHECKPOINT_3;

  $('chapter').textContent=info[0];
  $('mission').textContent=info[1];
  $('description').textContent=info[2];

  renderClues(st);

  $('count').textContent=
    `${st.reached_checkpoints.length} / 5`;

  const active=new Set(
    (st.checkpoints||[]).map(c=>Number(c.id))
  );

  const reached=new Set(
    st.reached_checkpoints||[]
  );

  // Hide future checkpoints.
  // Active checkpoints appear without their
  // actual location names until discovered.

  const visibleIds=new Set([
    ...active,
    ...reached
  ]);

  $('journey').innerHTML=[3,2,4,1,5]
    .filter(i=>visibleIds.has(i))
    .map(i=>`
      <div class="waypoint ${
        reached.has(i)?'done':'active'
      }">

        <span class="number">
          ${reached.has(i)?'✓':i}
        </span>

        ${
          reached.has(i)
            ?escapeHtml(CP[i].name)
            :`Checkpoint ${i} · Undiscovered`
        }

      </div>
    `).join('');

  // ======================================
  // INVENTORY
  // ======================================

  const relics=[];

  if(reached.has(2))
    relics.push('✦ Vayun · Enchanted Broom');

  if(reached.has(4))
    relics.push('✦ Aetheris · Wand');

  if(reached.has(1))
    relics.push('✦ Kavacha Nivara · Ward Spell');

  if(reached.has(5))
    relics.push('✦ Astra Seal & Guardian Ring');

  $('items').innerHTML=relics
    .map(t=>`<div class="item">${escapeHtml(t)}</div>`)
    .join('')||
    '<span class="muted">No relics discovered yet.</span>';

  s.deadline=st.deadline
    ?Date.parse(st.deadline)
    :null;

  $('clock-box').hidden=!s.deadline;

  updateClock();
  renderMap(st);

  if(st.messages?.length)
    enqueue(st.messages);

  if(
    (st.phase==='WON'||st.phase==='GAME_OVER') &&
    !s.endscreen
  ){
    s.endscreen=true;

    const win=st.phase==='WON';

    s.dialogQueue.push({
      speaker:win?'THE FINAL WARD':'THE DARKNESS',
      title:win?'IET-DAVV stands.':'The wards have fallen.',
      text:win
        ?'“Kavacha Nivara.” The Astra Seal and Guardian Ring awaken. A luminous shield surrounds the campus. The last attack breaks against its walls. You have won.'
        :'You could not complete the protection before time ran out. The campus wards fade. Your quest has ended.',
      art:win?'guardian':'dark',
      end:win
    });

    pump();
  }
}

// ======================================
// TIMER
// ======================================

function updateClock(){
  if(!s.deadline)return;

  const n=Math.max(
    0,
    Math.ceil((s.deadline-Date.now())/1000)
  );

  $('clock').textContent=
    `${String(Math.floor(n/60)).padStart(2,'0')}:`+
    `${String(n%60).padStart(2,'0')}`;

  $('clock-box').classList.toggle(
    'warning',
    n<=60
  );
}

// ======================================
// DIALOGUES
// ======================================

function enqueue(messages){
  for(const m of messages){

    const t=m.text||'';
    let entry=null;

    if(m.type==='checkpoint')
      entry={
        speaker:'LOCATION DISCOVERED',
        title:'A checkpoint awakens.',
        text:t,
        art:'guardian'
      };

    else if(m.type==='item')
      entry={
        speaker:'RELIC ACQUIRED',
        title:'The search pays off.',
        text:t,
        art:'guardian'
      };

    else if(m.type==='powerup')
      entry={
        speaker:'ENCHANTMENT ACTIVATED',
        title:'The search radius widens.',
        text:t,
        art:'guardian'
      };

    else if(m.type==='fight')
      entry={
        speaker:'BATTLE OF THE GROUNDS',
        title:'The Death Eaters retreat.',
        text:'With Aetheris in your hand and Vayun beneath you, you confront the advancing Death Eaters. A precise defensive charm turns the battle. The attackers retreat.',
        art:'dark'
      };

    else if(
      m.type==='story'&&
      /Hermione/i.test(t)
    )
      entry={
        speaker:'HERMIONE GRANGER',
        title:'A message through the wards.',
        text:t.replace(/^Hermione:\s*/i,''),
        art:'guardian'
      };

    else if(
      m.type==='story'&&
      /Death Eater/i.test(t)
    )
      entry={
        speaker:'A DEATH EATER',
        title:'A final warning.',
        text:t.replace(/^Death Eater:\s*/i,''),
        art:'dark'
      };

    else if(m.type==='gps_warning')
      notice(t);

    if(entry)
      s.dialogQueue.push(entry);
  }

  pump();
}

function pump(){
  if(
    s.dialogOpen||
    s.dialogQueue.length===0
  )return;

  const a=s.dialogQueue.shift();

  s.dialogOpen=true;

  $('scene-speaker').textContent=a.speaker;
  $('scene-title').textContent=a.title;
  $('scene-text').textContent=a.text;

  $('scene-img').src=
    `/assets/${a.art==='dark'?'dark':'guardian'}.svg`;

  $('scene-counter').textContent=
    `${s.dialogQueue.length} MORE EVENT${
      s.dialogQueue.length===1?'':'S'
    }`;

  $('scene-overlay').hidden=false;

  s.endscreen ||= !!a.end;
}

function dismiss(){
  if(!s.dialogOpen)return;

  s.dialogOpen=false;
  $('scene-overlay').hidden=true;

  if(s.dialogQueue.length){
    pump();
    return;
  }

  if(
    s.state&&
    ['WON','GAME_OVER'].includes(s.state.phase)
  ){
    finish(s.state.phase==='WON');
  }
}

// ======================================
// ENDING
// ======================================

function finish(win){
  show('ending');

  $('end-icon').textContent=win?'✶':'☾';

  $('end-kicker').textContent=
    win?'QUEST COMPLETE':'QUEST FAILED';

  $('end-headline').textContent=
    win
      ?'THE CAMPUS IS SAFE'
      :'THE WARDS HAVE FALLEN';

  $('end-desc').textContent=
    win
      ?'You recovered the lost magic and protected IET-DAVV. The last ward stands.'
      :'The countdown ended before the mission was complete. Every quest can begin again.';

  stopGps();
}

// ======================================
// GPS TRACKING
// ======================================

function stopGps(){
  if(s.watch!==null){
    navigator.geolocation.clearWatch(s.watch);
    s.watch=null;
  }
}

function locUI(pos){
  const c=pos.coords;

  $('gps').textContent='● GPS ACTIVE';
  $('accuracy').textContent=
    `±${Math.round(c.accuracy)}m`;

  s.locationTs=Date.now();

  if(!s.player){
    s.player=L.marker(
      [c.latitude,c.longitude],
      {
        icon:L.divIcon({
          className:'',
          html:'<div class="playerpin"></div>',
          iconSize:[17,17]
        })
      }
    ).addTo(s.map);

    s.map.setView(
      [c.latitude,c.longitude],
      17
    );
  }else{
    s.player.setLatLng([
      c.latitude,
      c.longitude
    ]);
  }
}

async function locationUpdate(pos){
  locUI(pos);

  if(
    s.requestBusy||
    !s.id||
    s.endscreen
  )return;

  s.requestBusy=true;

  try{
    const st=await request(
      `/api/game/${s.id}/location`,
      {
        method:'POST',
        body:JSON.stringify({
          latitude:pos.coords.latitude,
          longitude:pos.coords.longitude,
          accuracy:pos.coords.accuracy
        })
      }
    );

    render(st);

  }catch(e){
    notice(`Location update: ${e.message}`);
  }finally{
    s.requestBusy=false;
  }
}

function locationError(error){
  $('gps').textContent='○ GPS UNAVAILABLE';

  notice(
    error.code===1
      ?'Allow location access in your browser settings.'
      :'GPS unavailable: '+error.message
  );
}

function track(){
  if(!navigator.geolocation){
    notice('This browser cannot access location.');
    return;
  }

  stopGps();

  s.watch=navigator.geolocation.watchPosition(
    locationUpdate,
    locationError,
    {
      enableHighAccuracy:true,
      maximumAge:2000,
      timeout:16000
    }
  );
}

// ======================================
// SERVER REFRESH
// ======================================

function startRefresh(){
  clearInterval(s.poll);
  clearInterval(s.tick);

  s.poll=setInterval(async()=>{
    if(
      !s.id||
      s.requestBusy||
      s.endscreen
    )return;

    try{
      render(
        await request(`/api/game/${s.id}`)
      );
    }catch(e){
      notice(
        'Server connection lost: '+e.message
      );
    }
  },4000);

  s.tick=setInterval(updateClock,250);
}

// ======================================
// START GAME
// ======================================

async function start(){
  const name=$('name').value.trim();

  if(!name){
    notice('Enter your wizard name to continue.');
    return;
  }

  $('begin').disabled=true;

  try{
    const st=await request(
      '/api/game/start',
      {
        method:'POST',
        body:JSON.stringify({
          player_name:name
        })
      }
    );

    s.id=st.game_id;

    localStorage.setItem(
      'quest_game_id',
      s.id
    );

    s.endscreen=false;

    show('play');
    newMap();
    render(st);
    startRefresh();
    track();

  }catch(e){
    notice('Could not start: '+e.message);
  }finally{
    $('begin').disabled=false;
  }
}

// ======================================
// RESET GAME
// ======================================

async function reset(){
  if(!s.id)return;

  if(!confirm(
    'Restart this quest from checkpoint 3?'
  ))return;

  try{
    const st=await request(
      `/api/game/${s.id}/reset`,
      {method:'POST'}
    );

    // The server successfully restarted.
    // Restore the single-use hint.
    localStorage.removeItem(hintKey());

    s.dialogQueue=[];
    s.dialogOpen=false;
    s.endscreen=false;

    $('scene-overlay').hidden=true;

    show('play');
    newMap();
    render(st);
    startRefresh();
    track();

  }catch(e){
    notice('Could not restart: '+e.message);
  }
}

// ======================================
// BUTTON HANDLERS
// ======================================

$('begin').addEventListener('click',start);

$('name').addEventListener('keydown',e=>{
  if(e.key==='Enter')
    start();
});

$('next-scene').addEventListener('click',dismiss);
$('restart').addEventListener('click',reset);
$('again').addEventListener('click',reset);

// ======================================
// RESTORE PREVIOUS GAME
// ======================================

(async()=>{
  s.id=localStorage.getItem('quest_game_id');

  if(!s.id)return;

  try{
    const st=await request(`/api/game/${s.id}`);

    show('play');
    newMap();
    render(st);
    startRefresh();

    if(!['WON','GAME_OVER'].includes(st.phase))
      track();

  }catch{
    localStorage.removeItem('quest_game_id');
    s.id=null;
  }
})();
