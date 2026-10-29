import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from .model import Error
from .lexer import lex
from .parser import Parser
from .sema import analyze
from .ir import Lower
from .cgen import generate

def compile_source(source, path):
    ast = Parser(lex(source,path)).parse()
    symbols = analyze(ast)
    return Lower(symbols).lower(ast)

def main():
    p = argparse.ArgumentParser(description='Nat experimental AOT: typed IR -> C -> native executable')
    p.add_argument('command',choices=['check','emit-ir','emit-c','build'])
    p.add_argument('source',type=Path)
    p.add_argument('-o','--output',type=Path)
    p.add_argument('--cc',default='gcc')
    p.add_argument('--opt',choices=['0','2'],default='2')
    p.add_argument('--sanitize',action='store_true')
    args = p.parse_args()
    if args.command=='build' and args.output is None:
        p.error('build requiere -o ejecutable')
    if args.output and args.output.resolve()==args.source.resolve():
        p.error('La salida no puede sobrescribir la fuente.')
    try:
        ir = compile_source(args.source.read_text(encoding='utf-8'),str(args.source))
        if args.command=='check':
            return 0
        if args.command=='emit-ir':
            output = json.dumps(ir,indent=2,ensure_ascii=False)+'\n'
        else:
            output = generate(ir,str(args.source))
        if args.command=='build':
            args.output.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='natc-') as directory:
                source = Path(directory)/'program.c'
                source.write_text(output,encoding='utf-8')
                binary = Path(directory)/'program'
                command = [args.cc,'-std=c11','-O'+args.opt,'-Wall','-Wextra','-Werror','-Wpedantic',str(source),'-o',str(binary)]
                if args.sanitize:
                    command += ['-g','-fno-omit-frame-pointer','-fsanitize=address,undefined']
                    if sys.platform.startswith('linux'): command += ['-fno-pie','-no-pie']
                result = subprocess.run(command,capture_output=True,text=True)
                if result.returncode:
                    print(result.stderr,file=sys.stderr)
                    return 1
                # Copy to a sibling then replace, preserving any old output on failure.
                import shutil
                fd, staged = tempfile.mkstemp(dir=args.output.parent,prefix='.natc-')
                os.close(fd)
                try:
                    shutil.copy2(binary,staged)
                    os.replace(staged,args.output)
                finally:
                    if os.path.exists(staged): os.unlink(staged)
        elif args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(output,encoding='utf-8')
        else:
            print(output,end='')
        return 0
    except (Error,OSError,UnicodeError) as error:
        print(error,file=sys.stderr)
        return 1
    except RecursionError:
        print(f'{args.source}:1:1: Expresion/anidamiento demasiado profundo.',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
