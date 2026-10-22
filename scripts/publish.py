"""Publish an already-reviewed checkout using the caller's GitHub CLI session."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]

class PublishError(RuntimeError):
    pass

def run(*args,check=True):
    result=subprocess.run(args,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if check and result.returncode:
        raise PublishError(result.stderr.strip() or result.stdout.strip() or 'Comando falhou: '+args[0])
    return result

def validate_name(owner,name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}',owner): raise PublishError('Conta GitHub inválida')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}',name): raise PublishError('Nome de repositório inválido')
    return owner+'/'+name

def verify_asset(slug,data,apk):
    asset=next((item for item in data.get('assets',[]) if item['name']==apk.name),None)
    if asset is None: raise PublishError('Release sem o APK esperado; arquivos existentes não foram sobrescritos.')
    expected=hashlib.sha256(apk.read_bytes()).hexdigest()
    digest=asset.get('digest') or ''
    if digest.startswith('sha256:'):
        actual=digest.removeprefix('sha256:')
    else:
        with tempfile.TemporaryDirectory(prefix='mic-livre-release-') as directory:
            run('gh','release','download','v0.2.1','--repo',slug,'--pattern',apk.name,'--dir',directory)
            downloaded=Path(directory)/apk.name
            if not downloaded.is_file(): raise PublishError('O download do APK publicado não foi confirmado')
            actual=hashlib.sha256(downloaded.read_bytes()).hexdigest()
    if actual!=expected:
        raise PublishError('SHA-256 do APK publicado difere do APK local. Nenhum asset foi sobrescrito.')

def main(argv=None):
    parser=argparse.ArgumentParser(description='Criar repo público, enviar código/APK e configurar revisão de PRs')
    parser.add_argument('--owner',help='Conta/organização (padrão: conta autenticada no gh)')
    parser.add_argument('--name',default='mic-livre')
    parser.add_argument('--dry-run',action='store_true',help='Mostrar plano sem acessar a rede nem alterar o GitHub')
    args=parser.parse_args(argv)
    # Validate input before any authenticated request.
    validate_name(args.owner or 'conta-autenticada',args.name)
    if args.dry_run:
        print('Plano: criar '+(args.owner or '<conta-autenticada>')+'/'+args.name+' público;')
        print('enviar main/tag v0.2.1, publicar APK, exigir 1 aprovação e checks tests/android.')
        print('Nenhuma chamada à rede ou alteração foi feita.')
        return 0
    for command in ('git','gh'):
        if not shutil.which(command): raise PublishError('Instale '+command+' antes de publicar')
    if Path(run('git','rev-parse','--show-toplevel').stdout.strip()).resolve()!=ROOT:
        raise PublishError('O diretório precisa ser um repositório Git independente')
    if run('git','branch','--show-current').stdout.strip()!='main':
        raise PublishError('Publique a partir da branch main revisada')
    if run('git','status','--porcelain').stdout.strip():
        raise PublishError('Há mudanças sem commit. Revise e faça commit antes de publicar.')
    tag_sha=run('git','rev-parse','v0.2.1^{}').stdout.strip()
    if tag_sha!=run('git','rev-parse','HEAD').stdout.strip():
        raise PublishError('A tag v0.2.1 deve apontar para o commit que será publicado')
    tracked=run('git','ls-files').stdout.splitlines()
    if any(re.search(r'\.(p12|jks|keystore|pem)$',name,re.I) or Path(name).name.startswith('.env') for name in tracked):
        raise PublishError('Remova chaves/arquivos .env do índice antes de publicar')
    auth=run('gh','api','user','--jq','.login',check=False)
    if auth.returncode:
        raise PublishError('Sem acesso autenticado ao GitHub. Confira a rede e execute gh auth login no seu terminal.\n'+auth.stderr.strip())
    slug=validate_name(args.owner or auth.stdout.strip(),args.name)
    expected='https://github.com/'+slug+'.git'
    remote=run('git','remote','get-url','origin',check=False)
    if remote.returncode==0 and remote.stdout.strip() not in (expected,'git@github.com:'+slug+'.git'):
        raise PublishError('origin aponta para outro repositório. Não foi alterado.')
    existing=run('gh','api','repos/'+slug,check=False)
    if existing.returncode==0:
        if remote.returncode:
            raise PublishError('Esse repositório já existe e não é origin deste checkout. Escolha --name diferente.')
        if json.loads(existing.stdout).get('private'):
            raise PublishError('O repositório existente é privado. Sua visibilidade não foi alterada.')
    else:
        # Only a real 404 means it is safe to create; auth/rate/network errors do not.
        if '404' not in existing.stderr:
            raise PublishError('Não foi possível conferir se o repo existe: '+existing.stderr.strip())
        run('gh','repo','create',slug,'--public','--source',str(ROOT),'--remote','origin',
            '--description','Celular Android como microfone do Linux. Gratuito, código aberto e sem anúncios.')
    print('Enviando código para '+slug+'…',flush=True)
    run('git','push','-u','origin','main','refs/tags/v0.2.1')
    run('gh','api','--method','PATCH','repos/'+slug,'-f','default_branch=main','-F','allow_squash_merge=true',
        '-F','allow_merge_commit=false','-F','allow_rebase_merge=true','-F','delete_branch_on_merge=true')
    run('gh','api','--method','PUT','repos/'+slug+'/branches/main/protection',
        '--input',str(ROOT/'.github/branch-protection.json'))
    protection=json.loads(run('gh','api','repos/'+slug+'/branches/main/protection').stdout)
    if protection.get('required_pull_request_reviews',{}).get('required_approving_review_count')!=1:
        raise PublishError('O GitHub não confirmou a revisão obrigatória de PRs')
    if set(protection.get('required_status_checks',{}).get('contexts',[]))!={'tests','android'}:
        raise PublishError('O GitHub não confirmou os checks obrigatórios')
    release=run('gh','release','view','v0.2.1','--repo',slug,check=False)
    if release.returncode:
        run('gh','release','create','v0.2.1',str(ROOT/'apk/mic-livre-0.2.1.apk'),
            '--repo',slug,'--verify-tag','--title','Mic Livre 0.2.1',
            '--notes-file',str(ROOT/'docs/releases/0.2.1.md'))
    data=json.loads(run('gh','api','repos/'+slug+'/releases/tags/v0.2.1').stdout)
    verify_asset(slug,data,ROOT/'apk/mic-livre-0.2.1.apk')
    if run('gh','api','repos/'+slug+'/commits/main','--jq','.sha').stdout.strip()!=tag_sha:
        raise PublishError('O commit público da main não corresponde ao checkout local')
    repo=json.loads(run('gh','repo','view',slug,'--json','url,isPrivate').stdout)
    if repo['isPrivate']: raise PublishError('O GitHub não confirmou visibilidade pública')
    print('\nRepositório público verificado: '+repo['url'])
    print('Download do APK: '+data['html_url'])
    print('PRs exigem 1 aprovação e CI. Acompanhe os checks em '+repo['url']+'/actions')
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (PublishError,OSError,ValueError) as error:
        print('Publicação interrompida: '+str(error),file=sys.stderr)
        print('Se alguma etapa anterior criou o repo, ela foi preservada; corrija o erro e repita.',file=sys.stderr)
        sys.exit(1)
