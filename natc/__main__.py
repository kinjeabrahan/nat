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

def compile_source(source, path):
    ast = Parser(lex(source,path)).parse()
    symbols = analyze(ast)
    return Lower(symbols).lower()

def main():
    p = argparse.ArgumentParser(description='Nat experimental AOT: typed IR -> C -> native executable')
    p.add_argument('command',choices=['check','emit-ir','emit-c','emit-asm','build'])
    p.add_argument('source',type=Path)
    p.add_argument('-o','--output',type=Path)
    p.add_argument('--cc',default='gcc')
    p.add_argument('--backend',choices=['c','asm'],default='c')
    p.add_argument('--assembler',default='as')
    p.add_argument('--linker',default='ld')
    p.add_argument('--opt',choices=['0','2'],default=None,help='solo C; por defecto -O2')
    p.add_argument('--sanitize',action='store_true')
    args = p.parse_args()
    if args.command=='build' and args.output is None:
        p.error('build requiere -o ejecutable')
    if args.output and args.output.resolve()==args.source.resolve():
        p.error('La salida no puede sobrescribir la fuente.')
    if args.backend=='asm' or args.command=='emit-asm':
        import platform
        if sys.platform!='linux' or platform.machine() not in ('x86_64','AMD64'):
            p.error('asm requiere Linux x86_64.')
        if args.sanitize: p.error('--sanitize solo existe para C.')
        if args.opt is not None: p.error('--opt solo existe para C.')
    try:
        ir = compile_source(args.source.read_text(encoding='utf-8'),str(args.source))
        if args.command=='check':
            return 0
        if args.command=='emit-ir':
            output = json.dumps(ir,indent=2,ensure_ascii=False)+'\n'
        elif args.command=='emit-asm' or (args.command=='build' and args.backend=='asm'):
            from .asmgen import generate
            output = generate(ir,str(args.source))
        else:
            from .cgen import generate
            output = generate(ir,str(args.source))
        if args.command=='build':
            args.output.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='natc-') as directory:
                binary = Path(directory)/'program'
                if args.backend=='asm':
                    source = Path(directory)/'program.s'; source.write_text(output,encoding='utf-8')
                    obj = Path(directory)/'program.o'
                    commands = [[args.assembler,'--64',str(source),'-o',str(obj)],
                                [args.linker,'-m','elf_x86_64','-z','noexecstack',str(obj),'-o',str(binary)]]
                else:
                    source = Path(directory)/'program.c'; source.write_text(output,encoding='utf-8')
                    # Nat permits recursion, with a checked activation-depth limit.
                    command = [args.cc,'-std=c11','-O'+(args.opt or '2'),'-Wall','-Wextra','-Werror','-Wpedantic','-Wno-infinite-recursion',str(source),'-o',str(binary)]
                    if args.sanitize:
                        command += ['-g','-fno-omit-frame-pointer','-fsanitize=address,undefined']
                        if sys.platform.startswith('linux'): command += ['-fno-pie','-no-pie']
                    commands = [command]
                for command in commands:
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
