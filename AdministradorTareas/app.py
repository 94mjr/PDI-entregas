import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import threading
import time
import configparser
import xml.etree.ElementTree as ET
import os
from collections import defaultdict

DEFAULT_CFG = {
    "refresh_interval": "2",   
    "show_system_processes": "1", 
    "sort_by": "cpu",             
    "window_title": "Administrador de tareas - Python"
}

def load_ini(path):
    cp = configparser.ConfigParser()
    cp.read(path, encoding='utf-8')
    cfg = DEFAULT_CFG.copy()
    if 'app' in cp:
        for k in cfg:
            if k in cp['app']:
                cfg[k] = cp['app'][k]
    return cfg

def load_xml(path):
    cfg = DEFAULT_CFG.copy()
    tree = ET.parse(path)
    root = tree.getroot()
    for k in cfg:
        el = root.find(k)
        if el is not None and el.text:
            cfg[k] = el.text
    return cfg

class ProcessSampler:
    """
    Recopila métricas de procesos usando psutil.
    Mantiene últimas lecturas de io para calcular KB/s entre refrescos.
    """
    def __init__(self):
        self.last_io = {}  
        self.last_cpu_call = set()  
    def seed_cpu(self):
        for p in psutil.process_iter(attrs=[], ad_value=None):
            try:
                p.cpu_percent(interval=None)
            except Exception:
                pass

    def sample(self, show_system=True):
        """
        Retorna lista de dicts con: name, pid, cpu, mem_mb, io_kbs, connections
        """
        procs = []
        now = time.time()
        for proc in psutil.process_iter(attrs=['pid', 'name', 'username'], ad_value=None):
            try:
                info = proc.info
                pid = info['pid']
                name = info.get('name') or "<sin nombre>"
                username = info.get('username')
                if (not show_system) and (username is None or username == ""):
                    continue
                cpu = proc.cpu_percent(interval=None)

                mem = proc.memory_info().rss / (1024*1024)  
                try:
                    io = proc.io_counters()
                    read_bytes = io.read_bytes
                    write_bytes = io.write_bytes
                except Exception:
                    read_bytes = 0
                    write_bytes = 0

                last = self.last_io.get(pid)
                kbs = 0.0
                if last:
                    last_t, last_r, last_w = last
                    dt = now - last_t if now - last_t > 0 else 1.0
                    kbs = ((read_bytes - last_r) + (write_bytes - last_w)) / 1024.0 / dt
                self.last_io[pid] = (now, read_bytes, write_bytes)
                try:
                    conns = proc.connections(kind='inet')
                    conn_count = len(conns)
                except Exception:
                    conn_count = 0

                procs.append({
                    "name": name,
                    "pid": pid,
                    "cpu": round(cpu, 1),
                    "mem_mb": round(mem, 1),
                    "io_kbs": round(kbs, 1),
                    "connections": conn_count
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                continue
        return procs
class TaskManagerApp:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.root.title(cfg.get("window_title", DEFAULT_CFG["window_title"]))
        self.root.geometry("900x600")
        self.sampler = ProcessSampler()
        self.sampler.seed_cpu()

        self.refresh_interval = float(cfg.get("refresh_interval", "2"))
        self.show_system = bool(int(cfg.get("show_system_processes", "1")))
        self.sort_by = cfg.get("sort_by", "cpu")

        self._build_ui()
        self._start_background_refresh()

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=6)
        frm.pack(fill=tk.BOTH, expand=True)

       
        top = ttk.Frame(frm)
        top.pack(fill=tk.X, pady=(0,6))

        ttk.Label(top, text="Buscar:").pack(side=tk.LEFT, padx=(0,4))
        self.search_var = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.search_var)
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ent.bind("<Return>", lambda e: self.refresh_now())

        ttk.Button(top, text="Refrescar", command=self.refresh_now).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Finalizar tarea", command=self.end_task_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Forzar finalizar (kill)", command=self.kill_task_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Abrir Administrador Windows", command=self.open_windows_taskmgr).pack(side=tk.LEFT, padx=4)

        
        cols = ("name","pid","cpu","mem","io","net")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Nombre", anchor=tk.W)
        self.tree.heading("pid", text="PID")
        self.tree.heading("cpu", text="CPU %")
        self.tree.heading("mem", text="Mem (MB)")
        self.tree.heading("io", text="E/S disco (KB/s)")
        self.tree.heading("net", text="Conexiones")

        self.tree.column("name", anchor=tk.W, width=340)
        self.tree.column("pid", width=70, anchor=tk.CENTER)
        self.tree.column("cpu", width=80, anchor=tk.CENTER)
        self.tree.column("mem", width=100, anchor=tk.CENTER)
        self.tree.column("io", width=120, anchor=tk.CENTER)
        self.tree.column("net", width=90, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True)

       
        status = ttk.Frame(frm)
        status.pack(fill=tk.X, pady=(6,0))
        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(status, textvariable=self.status_var).pack(side=tk.LEFT)

     
        self.tree.bind("<Double-1>", self.on_double_click)

    def on_double_click(self, event):
        sel = self.tree.selection()
        if not sel: return
        pid = int(sel[0])
        self.show_details(pid)

    def show_details(self, pid):
        try:
            p = psutil.Process(pid)
            info = p.as_dict(attrs=['pid','name','exe','username','status','create_time','cpu_percent','memory_info'])
        except Exception as e:
            messagebox.showerror("Error", f"No se puede obtener info del proceso: {e}")
            return
        txt = ""
        for k,v in info.items():
            txt += f"{k}: {v}\n"
        messagebox.showinfo(f"Detalles PID {pid}", txt)

    def open_windows_taskmgr(self):
       
        try:
            import subprocess
            subprocess.Popen(["taskmgr"])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir Task Manager: {e}")

    def _start_background_refresh(self):
      
        self._stop_event = threading.Event()
        t = threading.Thread(target=self._bg_refresh_loop, daemon=True)
        t.start()

    def _bg_refresh_loop(self):
        while not self._stop_event.is_set():
            start = time.time()
            try:
                procs = self.sampler.sample(show_system=self.show_system)
              
                q = self.search_var.get().strip().lower()
                if q:
                    procs = [p for p in procs if q in p['name'].lower() or q in str(p['pid'])]
              
                key = None
                if self.sort_by == "cpu":
                    key = lambda x: x['cpu']
                    rev = True
                elif self.sort_by == "memory":
                    key = lambda x: x['mem_mb']
                    rev = True
                elif self.sort_by == "pid":
                    key = lambda x: x['pid']
                    rev = False
                else:
                    key = lambda x: x['name'].lower()
                    rev = False
                procs.sort(key=key, reverse=rev)
              
                self.root.after(0, lambda p=procs: self._update_tree(p))
                self.root.after(0, lambda: self.status_var.set(f"Último refresco: {time.strftime('%H:%M:%S')} - Procesos: {len(procs)}"))
            except Exception as e:
              
                self.root.after(0, lambda: self.status_var.set(f"Error muestreo: {e}"))
            elapsed = time.time() - start
            to_wait = max(0.1, self.refresh_interval - elapsed)
            time.sleep(to_wait)

    def _update_tree(self, procs):
      
        cur = set(self.tree.get_children())
        new_ids = set()
        for p in procs:
            pid = str(p['pid'])
            new_ids.add(pid)
            vals = (p['name'], p['pid'], p['cpu'], p['mem_mb'], p['io_kbs'], p['connections'])
            if pid in cur:
             
                self.tree.item(pid, values=vals)
            else:
               
                self.tree.insert("", tk.END, iid=pid, values=vals)
       
        for old in cur - new_ids:
            self.tree.delete(old)

    def refresh_now(self):
       
        def f():
            procs = self.sampler.sample(show_system=self.show_system)
            q = self.search_var.get().strip().lower()
            if q:
                procs = [p for p in procs if q in p['name'].lower() or q in str(p['pid'])]
          
            key = (lambda x: x['cpu']) if self.sort_by == "cpu" else (lambda x: x['name'].lower())
            procs.sort(key=key, reverse=(self.sort_by=="cpu"))
            self.root.after(0, lambda p=procs: self._update_tree(p))
        threading.Thread(target=f, daemon=True).start()

    def end_task_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        try:
            p = psutil.Process(pid)
            p.terminate()
            gone, alive = psutil.wait_procs([p], timeout=3)
            if alive:
                messagebox.showwarning("Atención", f"El proceso PID {pid} no respondió al terminate. Usá 'Forzar finalizar' para matar.")
            else:
                messagebox.showinfo("Hecho", f"Proceso PID {pid} terminado.")
        except psutil.NoSuchProcess:
            messagebox.showinfo("Info", "El proceso ya no existe.")
        except psutil.AccessDenied:
            messagebox.showerror("Permiso denegado", "No tenés permisos para terminar este proceso (ejecutá como Administrador).")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        self.refresh_now()

    def kill_task_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        try:
            p = psutil.Process(pid)
            p.kill()
            messagebox.showinfo("Hecho", f"Proceso PID {pid} fue forzado a finalizar.")
        except psutil.NoSuchProcess:
            messagebox.showinfo("Info", "El proceso ya no existe.")
        except psutil.AccessDenied:
            messagebox.showerror("Permiso denegado", "No tenés permisos para matar este proceso (ejecutá como Administrador).")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        self.refresh_now()

    def stop(self):
        self._stop_event.set()


def main():
    
    cfg = DEFAULT_CFG.copy()
    if os.path.exists("config.ini"):
        try:
            cfg.update(load_ini("config.ini"))
        except Exception:
            pass
    elif os.path.exists("config.xml"):
        try:
            cfg.update(load_xml("config.xml"))
        except Exception:
            pass

    root = tk.Tk()
    app = TaskManagerApp(root, cfg)

    def on_close():
        app.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
