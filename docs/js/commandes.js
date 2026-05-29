function toggle(hdr){hdr.classList.toggle('open');hdr.nextElementSibling.classList.toggle('open');}

document.querySelectorAll('.cat').forEach(cat=>{
  const id=cat.dataset.id;
  const el=document.getElementById('c-'+id);
  const n=cat.querySelectorAll('.cmd').length;
  if(el) el.textContent=n+' commande'+(n>1?'s':'');
});

function filter(){
  const q=document.getElementById('si').value.toLowerCase().trim();
  document.querySelectorAll('.cat').forEach(cat=>{
    let vis=0;
    cat.querySelectorAll('.cmd').forEach(cmd=>{
      const name=cmd.querySelector('.cmd-name').textContent.toLowerCase();
      const desc=cmd.querySelector('.cmd-desc').textContent.toLowerCase();
      const match=!q||name.includes(q)||desc.includes(q);
      cmd.style.display=match?'':'none';
      if(match)vis++;
    });
    cat.style.display=(!q||vis>0)?'':'none';
    if(q){cat.querySelector('.cat-hdr').classList.add('open');cat.querySelector('.cmd-list').classList.add('open');}
  });
}
