/* MedCompanion — shared Pro-tool gate (free 5/month for clinicians, unlimited on Pro).
   Enforced ONLY when billing gating is ON; otherwise everything stays open. */
(function(){
  var cfg={gating:false};
  function testOn(){ try{ return localStorage.getItem('mc_gating_test')==='1'; }catch(e){ return false; } }
  try{ fetch('/billing-config').then(function(r){return r.json();}).then(function(c){ if(c) cfg=c; }).catch(function(){}); }catch(e){}
  function tier(){ try{ return localStorage.getItem('mc_tier')||'free'; }catch(e){ return 'free'; } }
  var FREE_MONTHLY=5;
  function paywall(){
    var id='mcProPay'; if(document.getElementById(id)) { document.getElementById(id).style.display='flex'; return; }
    var d=document.createElement('div'); d.id=id;
    d.style.cssText='position:fixed;inset:0;z-index:100000;background:rgba(6,20,15,.66);display:flex;align-items:center;justify-content:center;padding:20px';
    d.innerHTML='<div style="background:#12211a;border:1px solid rgba(255,255,255,.12);border-radius:20px;max-width:400px;width:100%;padding:26px;text-align:center;box-shadow:0 26px 70px rgba(0,0,0,.55);font-family:system-ui,-apple-system,sans-serif;color:#e9f2ec">'
      +'<div style="font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#7fe6b4;background:rgba(52,199,140,.14);border-radius:999px;padding:5px 12px;display:inline-block">MedCompanion Pro</div>'
      +'<div style="font-size:21px;font-weight:850;margin:14px 0 6px">You&rsquo;ve used your 5 free this month</div>'
      +'<div style="font-size:14.5px;color:#cfe3d8;line-height:1.55;margin:0 0 18px">Upgrade to <b>Pro</b> for unlimited patient handouts, visit summaries, and chronologies for your practice.</div>'
      +'<a href="/founding" style="display:block;background:#34c78c;color:#062418;text-decoration:none;font-weight:800;font-size:15px;padding:13px;border-radius:12px">See Pro plans →</a>'
      +'<button onclick="document.getElementById(\'mcProPay\').style.display=\'none\'" style="background:none;border:none;color:#8fbfa8;font-size:13.5px;margin-top:12px;cursor:pointer">Maybe later</button>'
      +'</div>';
    d.addEventListener('click',function(e){ if(e.target===d) d.style.display='none'; });
    document.body.appendChild(d);
  }
  window.mcProGate=function(tool){
    var gating = cfg.gating || testOn();
    if(!gating) return true;              // gating OFF -> open
    if(tier()==='pro') return true;       // Pro tier -> unlimited
    var k='mc_pro_used_'+(new Date().toISOString().slice(0,7));   // per calendar month
    var used=parseInt(localStorage.getItem(k)||'0',10);
    if(used>=FREE_MONTHLY){ paywall(); return false; }
    try{ localStorage.setItem(k, used+1); }catch(e){}
    return true;
  };
})();
