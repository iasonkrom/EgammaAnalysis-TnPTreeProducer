#!/bin/env python
import os

#
# Example script to submit TnPTreeProducer to crab
#
submitVersion = "2024-07-02" # add some date here
doL1matching  = False
isAOD = False

defaultArgs   = ['doEleID=True','doPhoID=True','doTrigger=True']
AODArgs     = ['isAOD=True','doRECO=True']
mainOutputDir = '/store/group/phys_egamma/tnpTuples/%s/%s' % (os.environ['USER'], submitVersion)

# Logging the current version of TnpTreeProducer here, such that you can find back what the actual code looked like when you were submitting
# os.system('mkdir -p /eos/cms/%s' % mainOutputDir)
# os.system('(git log -n 1;git diff) &> /eos/cms/%s/git.log' % mainOutputDir)


#
# Common CRAB settings
#
from CRABClient.UserUtilities import config
config = config()

config.General.requestName             = ''
config.General.transferLogs            = False
config.General.workArea                = 'crab_%s' % submitVersion

config.JobType.pluginName              = 'Analysis'
config.JobType.psetName                = '../python/TnPTreeProducer_cfg.py'
config.JobType.sendExternalFolder      = True
config.JobType.allowUndistributedCMSSW = True

config.Data.inputDataset               = ''
config.Data.inputDBS                   = 'global'
config.Data.publication                = False
config.Data.allowNonValidInputDataset  = True
config.Site.storageSite                = 'T2_CH_CERN'


#
# Certified lumis for the different eras
#   (seems the JSON for UL2017 is slightly different from rereco 2017, it's not documented anywhere though)
#
def getLumiMask(era):
  if   era=='2016':   return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions16/13TeV/ReReco/Final/Cert_271036-284044_13TeV_23Sep2016ReReco_Collisions16_JSON.txt'
  elif era=='2017':   return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions17/13TeV/ReReco/Cert_294927-306462_13TeV_EOY2017ReReco_Collisions17_JSON_v1.txt'
  elif era=='2018':   return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions18/13TeV/PromptReco/Cert_314472-325175_13TeV_PromptReco_Collisions18_JSON.txt'
  elif era=='UL2016preVFP': return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions16/13TeV/Legacy_2016/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt'
  elif era=='UL2016postVFP': return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions16/13TeV/Legacy_2016/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt'
  elif era=='UL2017': return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions17/13TeV/Legacy_2017/Cert_294927-306462_13TeV_UL2017_Collisions17_GoldenJSON.txt'
  elif era=='UL2018': return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions18/13TeV/PromptReco/Cert_314472-325175_13TeV_PromptReco_Collisions18_JSON.txt'
  elif era=='2022': return 'https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/Cert_Collisions2022_355100_362760_Golden.json'
  elif era=='2023': return 'https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/Cert_Collisions2023_366442_370790_Golden.json'
  elif era=='2024': return 'https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions24/DCSOnly_JSONS/dailyDCSOnlyJSON/Collisions24_13p6TeV_378981_382595_DCSOnly_TkPx.json'


#
# Submit command
#
from CRABAPI.RawCommand import crabCommand
from CRABClient.ClientExceptions import ClientException
from http.client import HTTPException

def submit(config, requestName, sample, era, json, extraParam=[]):
  isMC                        = 'SIM' in sample
  config.General.requestName  = '%s_%s' % (era, requestName)
  config.Data.inputDataset    = sample
  config.Data.outLFNDirBase   = '%s/%s/%s/' % (mainOutputDir, era, 'mc' if isMC else 'data')
  config.Data.splitting       = 'FileBased' if isMC else 'LumiBased'
  config.Data.lumiMask        = None if isMC else json
  config.Data.unitsPerJob     = 5 if isMC else 25
  config.JobType.pyCfgParams  = (defaultArgs if not isAOD else AODArgs) + ['isMC=True' if isMC else 'isMC=False', 'era=%s' % era] + extraParam

  print( config )
  outF = open('crab_submit_%s.py'%requestName, 'w')
  print( config, file=outF)
  outF.close()
  try:                           crabCommand('submit', config = config)
  except HTTPException as hte:   print( "Failed submitting task: %s" % (hte.headers))
  except ClientException as cle: print( "Failed submitting task: %s" % (cle))
  print()
  print()

#
# Wrapping the submit command
# In case of doL1matching=True, vary the L1Threshold and use sub-json
#
from multiprocessing import Process
def submitWrapper(requestName, sample, era, extraParam=[]):
  if doL1matching:
    from getLeg1ThresholdForDoubleEle import getLeg1ThresholdForDoubleEle
    for leg1Threshold, json in getLeg1ThresholdForDoubleEle(era.replace("UL","").replace("preVFP","").replace("postVFP","")):
      print( 'Submitting for leg 1 threshold %s' % (leg1Threshold))
      p = Process(target=submit, args=(config, '%s_leg1Threshold%s' % (requestName, leg1Threshold), sample, era, json, extraParam + ['L1Threshold=%s' % leg1Threshold]))
      p.start()
      p.join()
  else:
    p = Process(target=submit, args=(config, requestName, sample, era, getLumiMask(era), extraParam))
    p.start()
    p.join()
    #submit(config, requestName, sample, era, getLumiMask(era), extraParam) # print the config files


#
# List of samples to submit, with eras
# Here the default data/MC for UL and rereco are given (taken based on the release environment)
# If you would switch to AOD, don't forget to add 'isAOD=True' to the defaultArgs!
#
#from EgammaAnalysis.TnPTreeProducer.cmssw_version import isReleaseAbove
#if isReleaseAbove(13,0):

eraData       = '2024'

submitWrapper('Run2024E_0v1', '/EGamma0/Run2024E-PromptReco-v1/MINIAOD', eraData)
submitWrapper('Run2024E_1v1', '/EGamma1/Run2024E-PromptReco-v1/MINIAOD', eraData)
submitWrapper('Run2024E_0v2', '/EGamma0/Run2024E-PromptReco-v2/MINIAOD', eraData)
submitWrapper('Run2024E_1v2', '/EGamma1/Run2024E-PromptReco-v2/MINIAOD', eraData)
submitWrapper('Run2024F_0v1', '/EGamma0/Run2024F-PromptReco-v1/MINIAOD', eraData)
submitWrapper('Run2024F_1v1', '/EGamma1/Run2024F-PromptReco-v1/MINIAOD', eraData)

if isAOD:  #AOD files

    submitWrapper('Run2024E_0v1_AOD', '/EGamma0/Run2024E-PromptReco-v1/AOD', eraData)
    submitWrapper('Run2024E_1v1_AOD', '/EGamma1/Run2024E-PromptReco-v1/AOD', eraData)
    submitWrapper('Run2024E_0v2_AOD', '/EGamma0/Run2024E-PromptReco-v2/AOD', eraData)
    submitWrapper('Run2024E_1v2_AOD', '/EGamma1/Run2024E-PromptReco-v2/AOD', eraData)
    submitWrapper('Run2024F_0v1_AOD', '/EGamma0/Run2024F-PromptReco-v1/AOD', eraData)
    submitWrapper('Run2024F_1v1_AOD', '/EGamma1/Run2024F-PromptReco-v1/AOD', eraData)
