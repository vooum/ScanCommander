#!/usr/bin/env python3
from command import *
import subprocess,random,math,shutil
#print([ i for i in globals().keys() if '__' not in i])


# settings
ism='M_h2'
target=1000
StepFactor=1. # sigma = n% of (maximum - minimum) of the free parameters
SlopFactor=.3 # difficulty of accepting a new point with higher chisq
add_chisq=True
ignore=[ 'Landau Pole'#27
        ,'excluded by Planck'#30
        ,'b->s gamma'#32
        ,'B_s->mu+mu-'#35
        ,'No Higgs in the MHmin-MHmax'#46
        ,'Relic density'#
        ,'b -> c tau nu'    # always keep alive
        ]
r=readSLHA(discountKeys=ignore)

#print(read.readline.readline)
#print(mcmc.Scan)

free=mcmc.Scan()
#free.add(name,block,PDG,min,max,walk='flat',step=None,value=None)
free.add('tanB','MINPAR',3,2.,60.,step=None)
free.add('M1','EXTPAR',1  ,20.    ,1000.,step=None)
free.add('M2'	,'EXTPAR'   ,2  ,100.    ,2000.,step=None)
free.add('Atop'	,'EXTPAR'   ,11  ,  -6e3    ,6e3,step=None)
free.add('Abottom','EXTPAR'   ,12,-6e3,6e3,walk=free.Atop)
free.add('Atau'	,'EXTPAR'   ,13  ,  100.      ,2000.,step=None)
free.add('MtauL','EXTPAR'   ,33,	100.,	2.e3,walk=free.Atau)
free.add('MtauR','EXTPAR'   ,36,	100.,	2.e3,walk=free.Atau)
free.add('MQ3L'	,'EXTPAR'   ,43,	100.,	2.e3,step=None)
free.add('MtopR'	,'EXTPAR'   ,46,	100.,	2.e3,step=None)
free.add('MbottomL','EXTPAR'  ,49,	100.,	2.e3 ,walk=free.MtopR)
free.add('lambda','EXTPAR'  ,61  ,1e-3    ,1. ,walk='log',step=None)
free.add('kappa','EXTPAR'   ,62 ,1.e-3    ,1. ,walk='log',step=None)
free.add('A_kappa','EXTPAR' ,64,-3.e3,3.e3,step=None)
free.add('mu_eff','EXTPAR'  ,65,100.,1500.,step=None)
free.add('MA','EXTPAR',124,	0.,	2.e3)

# read start points================================
inpModel=open(inpModelDir,'r')
inpModelLines=inpModel.readlines()
inpModel.close()
if True:
    BLOCK=''
    for line in inpModelLines:
        a=readline(line)
        if a[-1] and a[0]=='BLOCK':
            BLOCK=a[1]
        else:
            if hasattr(free,BLOCK):
                P=getattr(free,BLOCK)
                if a[0] in P.keys():
                    P[a[0]].value=a[1]

free.SetRandom()

L_Nsd=DarkMatter('LUX2016_Nsd.txt')
L_Psd=DarkMatter('LUX2016_Psd.txt')
L_Psi=DarkMatter('LUX2016_Psi.txt')

record=-1
trypoint=0
lastchisq=1e10
# scan ==================================================================
while record < target:

    if trypoint%100==1: print(trypoint,' points tried; ',record,' points recorded')
    trypoint+=1

    # rewrite inp-------------------------------------------------------
    inp=open(inpDir,'w')
    BLOCK = ''
    Nnewline=0
    for line in inpModelLines:
        newline=''
        a=readline(line)
        if a[0]=='BLOCK':
            BLOCK = a[1]
        else:
            if hasattr(free,BLOCK):
                P=getattr(free,BLOCK)
                if a[0] in P.keys():
                    i=P[a[0]]
                    newline='\t'+'\t'.join([str(i.PDG),str(i.new_value),a[-2]])+'\n'
        if newline == '':		#output mcmcinp
      	    inp.write(line)
        else:   #inp.write('#--- original line'+line)
            inp.write(newline)
    inp.close()

#--------- run nmhdecay.f ----------------------
    f1=open('err.log','w')
    nmhdecay =  subprocess.Popen(run
  	    ,stderr=f1, stdout=f1, cwd=NMSSMToolsDir, shell=True).wait()

#--------- read output ------------------------
    if not os.path.exists(spectrDir): exit('spectr.dat not exist')

    r.read(spectrDir)
    '''
    print(sorted(r.Decay.__dict__))
    print(list(r.__dict__.keys()))
    print(r.Decay.St_1)
    exit()'''

    if r.p:
        mainNNo=0
        mixV=0
        for i in range(5):
            if abs(r.Nmix[tuple([1,i+1])]) > abs(mixV):
                mixV=r.Nmix[tuple([1,i+1])]
                mainNNo=i+1
        
        #if mainNNo not in [3,4,5]:continue
        if 'csNsd' in r.DM.keys():
            if abs(r.DM['csNsd'])>L_Nsd.value(r.Msp['X_N1']):continue
            if abs(r.DM['csPsd'])>L_Psd.value(r.Msp['X_N1']):continue
            if abs(r.DM['csPsi'])>L_Psi.value(r.Msp['X_N1']):continue
        if r.__hasattr__('HBresult'):
            if r.HBresult!=1:continue
        if r.__hasattr__('HSresult'):
            if r.HSresult<0.05:continue
        chisq=0.
        chisq_Q={}
        chisq_A={}
        # chisqure
        chisq_Q['mh']=chi2(r.Mh[ism],mh)
        chisq_Q['bsg']=chi2(r.b_phy['b_sg']*1e4,bsg)
        chisq_Q['bmu']=chi2(r.b_phy['b_mu']*1e9,bmu)
        chisq_Q['DM']=chi2(r.DM['DMRD'],omg)
        #chisq_A['FT']=(max(r.FT,40.)-40.)**2/100.
        for i in chisq_Q.values():
            chisq+=i
        if add_chisq :
            for i in chisq_A.values(): 
                chisq+=i
        #   record point
        if (random.random() < math.exp(max(SlopFactor*min(lastchisq-chisq,0.),-745))
    	    or chisq<10.):
            lastchisq=chisq
            free.record()
            print(record,'points recorded.')
            print('\nnew point accepted: -------------------')
            print('x2=  ',chisq,'\nx2_i= ',chisq_Q,chisq_A)
            print('Higgs masses: ',r.Mh)
            free.print()

            record+=1
            shutil.copyfile(inpDir,os.path.join(recordDir,'inp.'+str(record)))
            shutil.move(spectrDir,os.path.join(recordDir,'spectr.'+str(record)))
            shutil.move(omegaDir,os.path.join(recordDir,'omega.'+str(record)))

    free.GetNewPoint(StepFactor)