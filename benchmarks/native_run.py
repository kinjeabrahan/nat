"""Native recurrence benchmark. No source parsing is performed during Nat execution."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent

def timed(command):
    start=time.perf_counter_ns()
    r=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,timeout=60)
    elapsed=(time.perf_counter_ns()-start)/1e9
    if r.returncode: raise RuntimeError(r.stderr.decode(errors='replace'))
    return r,elapsed

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'build/native-benchmark.json')
    p.add_argument('--iterations',type=int,default=2000000)
    p.add_argument('--repetitions',type=int,default=9)
    a=p.parse_args()
    if not 0<=a.iterations<=2000000 or a.repetitions<3: p.error('iterations 0..2000000; repetitions >=3')
    build=ROOT/'build/native-benchmark'; build.mkdir(parents=True,exist_ok=True)
    source=HERE/'native_kernel'
    gcc=shutil.which('gcc')
    if not gcc: p.error('GCC requerido')
    flags=['-std=c11','-O2','-Wall','-Wextra','-Werror','-Wpedantic']
    _,front=timed([sys.executable,'-m','natc','emit-c',source.with_suffix('.nat'),'-o',build/'nat.c'])
    implementations={}; commands={}
    def compile(name,command,binary,frontend=0):
        _,elapsed=timed(command)
        implementations[name]={'compile_command':list(map(str,command)),'frontend_seconds':frontend,
            'backend_seconds':elapsed,'compile_seconds':frontend+elapsed,'samples_seconds':[]}
        commands[name]=[str(binary),str(a.iterations)]
    compile('Nat',[gcc,*flags,build/'nat.c','-o',build/'nat'],build/'nat',front)
    compile('C',[gcc,*flags,source.with_suffix('.c'),'-o',build/'c'],build/'c')
    cpp=shutil.which('g++')
    if cpp: compile('C++',[cpp,'-x','c++','-std=c++17','-O2',source.with_suffix('.c'),'-o',build/'cpp'],build/'cpp')
    else: implementations['C++']={'status':'unavailable'}
    rust=shutil.which('rustc')
    if rust: compile('Rust',[rust,'-C','opt-level=2',source.with_suffix('.rs'),'-o',build/'rust'],build/'rust')
    else: implementations['Rust']={'status':'unavailable'}
    pyc=build/'python.pyc'
    _,elapsed=timed([sys.executable,'-c','import py_compile,sys; py_compile.compile(sys.argv[1],cfile=sys.argv[2],doraise=True)',source.with_suffix('.py'),pyc])
    implementations['Python']={'compile_seconds':elapsed,'compile_kind':'py_compile subprocess to bytecode','samples_seconds':[]}
    commands['Python']=[sys.executable,str(pyc),str(a.iterations)]
    x=1
    for i in range(a.iterations): x=(x*17+i)%1000003
    expected=(str(x)+'\n').encode()
    for name,cmd in commands.items():
        for _ in range(2):
            result,_=timed(cmd)
            assert result.stdout==expected and not result.stderr,name
    rng=random.Random(42)
    for _ in range(a.repetitions):
        order=list(commands); rng.shuffle(order)
        for name in order:
            result,elapsed=timed(commands[name])
            assert result.stdout==expected and not result.stderr,name
            implementations[name]['samples_seconds'].append(elapsed)
    for name in commands:
        record=implementations[name]; values=record['samples_seconds']
        record.update(status='measured',median_seconds=statistics.median(values),
                      stdev_seconds=statistics.stdev(values),min_seconds=min(values),max_seconds=max(values),
                      run_command=commands[name],verified_stdout=expected.decode())
        print(name, 'compile',round(record['compile_seconds'],6),'s; run median',round(record['median_seconds']*1000,3),'ms')
    versions={tool:subprocess.run([path,'--version'],capture_output=True,text=True).stdout.splitlines()[0]
              for tool,path in [('gcc',gcc),('g++',cpp),('rustc',rust)] if path}
    cpu=next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),platform.processor())
    report={'date_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'cpu':cpu,
            'versions':versions,'python':sys.version,'iterations':a.iterations,'repetitions':a.repetitions,'warmups':2,
            'sources_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()
                              for f in [*HERE.glob('native_kernel.*'),* (ROOT/'natc').glob('*.py'),ROOT/'natc/runtime.h']},
            'limitations':['One integer recurrence only; no memory/IO workloads','Process startup included; no CPU isolation or frequency control',
                          'C/C++ and Nat use checked arithmetic; Python uses arbitrary precision but values fit Int64',
                          'Python compilation measured separately to pyc; execution still needs Python VM',
                          'Compilation timings are single samples; not compilation performance distributions'],
            'implementations':implementations}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__': main()
