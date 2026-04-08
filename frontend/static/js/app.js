const api = (p)=>`/api${p}`;
const token = ()=>localStorage.getItem('access_token');
const headers = ()=> token()? { 'Content-Type':'application/json', 'Authorization':`Bearer ${token()}` } : { 'Content-Type':'application/json' };

const registerForm = document.getElementById('registerForm');
if(registerForm){
  registerForm.addEventListener('submit', async (e)=>{
    e.preventDefault();
    const data = Object.fromEntries(new FormData(registerForm).entries());
    const res = await fetch(api('/auth/register'), {method:'POST', headers: headers(), body: JSON.stringify(data)});
    let msg = 'Registration failed';
    try { const j = await res.json(); msg = j.msg || msg; } catch {}
    document.getElementById('registerMsg').textContent = res.ok ? 'Registered. Please login.' : msg;
  });
}

const loginForm = document.getElementById('loginForm');
if(loginForm){
  loginForm.addEventListener('submit', async (e)=>{
    e.preventDefault();
    const data = Object.fromEntries(new FormData(loginForm).entries());
    const res = await fetch(api('/auth/login'), {method:'POST', headers: headers(), body: JSON.stringify(data)});
    const j = await res.json();
    if(res.ok){
      // Clear any stale auth state first (prevents role mismatch 403s)
      localStorage.removeItem('access_token');
      localStorage.removeItem('token');
      localStorage.removeItem('user_role');
      localStorage.removeItem('warehouse_location');

      // Persist token consistently across the app
      localStorage.setItem('access_token', j.access_token);
      localStorage.setItem('token', j.access_token); // legacy key used by some older code
      if(j.role) localStorage.setItem('user_role', String(j.role).toLowerCase());

      // Persist warehouse_location for warehouse users (used by warehouse dashboard)
      try{
        const payload = JSON.parse(atob(String(j.access_token).split('.')[1] || ''));
        if(payload && payload.warehouse_location){
          localStorage.setItem('warehouse_location', payload.warehouse_location);
        }
      }catch(e){}

      const pathMap = { '/farmer':'/farmer','/warehouse':'/warehouse','/exporter':'/exporter','/logistics':'/logistics','/government':'/government','/admin':'/admin'};
      window.location.href = pathMap[j.redirect] || '/';
    } else {
      document.getElementById('loginMsg').textContent = j.msg || 'Login failed';
    }
  });
}
