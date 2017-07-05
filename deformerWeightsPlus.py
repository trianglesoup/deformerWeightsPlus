'''
DeformerWeightsPlus - A bare bones wrapper for the deformerWeights command.
Christopher Evans, Version 0.1, Oct 2016
@author = Chris Evans
version = 0.1

Disclaimer: This was created on Epic Friday, a day where Epic employees can work on whatever we want, but is not owned/managed by Epic Games.
'''

import os
import time
import tempfile
import xml.etree.ElementTree


#from PySide import QtGui, QtCore
#import shiboken

import maya.cmds as cmds
import maya.OpenMayaUI as mui
import maya.mel as mel

import PySide2.QtGui as QtGui
import PySide2.QtCore as QtCore
import PySide2.QtWidgets as QtWidgets
import shiboken2

def show():
    global deformerWeightsPlusWindow
    try:
        deformerWeightsPlusWindow.close()
    except:
        pass

    deformerWeightsPlusWindow = DeformerWeightsPlus()
    deformerWeightsPlusWindow.show()
    return deformerWeightsPlusWindow

def getMayaWindow():
    ptr = mui.MQtUtil.mainWindow()
    if ptr is not None:
        return shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)

def isMesh(node):
    rels = cmds.listRelatives(node, children=True, s=True)
    if rels:
        for shp in rels:
            if cmds.nodeType(shp)=='mesh':
                return True
    return False

def removeUnusedInfluences(mesh):
    if isMesh(mesh):
        skin = findRelatedSkinCluster(mesh)
        print skin, mesh
        for inf in cmds.skinCluster(skin, inf=1, q=1):
            if inf not in cmds.skinCluster(skin, weightedInfluence=1, q=1):
                cmds.skinCluster(skin, e=1, ri=inf)

def findRelatedSkinCluster(node):
    skinClusters = cmds.ls(type='skinCluster')

    for cluster in skinClusters:
        geometry = cmds.skinCluster(cluster, q=True, g=True)[0]
        geoTransform = cmds.listRelatives(geometry, parent=True)[0]

        dagPath = cmds.ls(geoTransform, long=True)[0]

        if geoTransform == node:
            return cluster
        elif dagPath == node:
            return cluster


## USER INTERFACE
class DeformerWeightsPlus(QtWidgets.QDialog):
    def __init__(self, parent=getMayaWindow(), debug=0):
        
        #quick UI stuff
        QtWidgets.QDialog.__init__(self, parent)
        self.resize(350, 160)
        self.verticalLayout = QtWidgets.QVBoxLayout(self)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setContentsMargins(3, 3, 3, 3)
        self.exportBTN = QtWidgets.QPushButton(self)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setWeight(75)
        font.setBold(True)
        self.exportBTN.setFont(font)
        self.exportBTN.setObjectName("exportBTN")
        self.verticalLayout.addWidget(self.exportBTN)
        self.exportBTN.setText("EXPORT SKIN WEIGHTS")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.useTempCHK = QtWidgets.QCheckBox(self)
        self.useTempCHK.setChecked(True)
        self.useTempCHK.setObjectName("useTempCHK")
        self.useTempCHK.setText('Use a tempDir')
        self.horizontalLayout_2.addWidget(self.useTempCHK)
        self.pathLINE = QtWidgets.QLineEdit(self)
        self.pathLINE.setEnabled(False)
        self.pathLINE.setObjectName("pathLINE")
        self.horizontalLayout_2.addWidget(self.pathLINE)
        self.pathBTN = QtWidgets.QPushButton(self)
        self.pathBTN.setEnabled(False)
        self.pathBTN.setMaximumSize(QtCore.QSize(25, 16777215))
        self.pathBTN.setObjectName("pathBTN")
        self.pathBTN.setText('...')
        self.horizontalLayout_2.addWidget(self.pathBTN)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.importSkinWeightsBTN = QtWidgets.QPushButton(self)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setWeight(75)
        font.setBold(True)
        self.importSkinWeightsBTN.setFont(font)
        self.importSkinWeightsBTN.setObjectName("importSkinWeightsBTN")
        self.importSkinWeightsBTN.setText("IMPORT SKIN WEIGHTS")
        self.verticalLayout.addWidget(self.importSkinWeightsBTN)
        self.outputWin = QtWidgets.QTextEdit(self)
        self.outputWin.setObjectName("outputWin")
        self.verticalLayout.addWidget(self.outputWin)
        self.setWindowTitle("Save/Load skinWeights - (DeformerWeights+)")
        
        #connect UI
        self.exportBTN.clicked.connect(self.exportFn)
        self.importSkinWeightsBTN.clicked.connect(self.importFn)
        
        QtCore.QObject.connect(self.useTempCHK, QtCore.SIGNAL("toggled(bool)"), self.pathLINE.setDisabled)
        QtCore.QObject.connect(self.useTempCHK, QtCore.SIGNAL("toggled(bool)"), self.pathBTN.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(self)
        
        self.output = 'Initialized.\n'
        self.refreshUI()
        self.setTempPath()
        
    def refreshUI(self):
        self.outputWin.setText(self.output)
        
    def exportFn(self):
        meshSel = [m for m in cmds.ls(sl=1) if isMesh(m)]
        if meshSel:
            sdw = SkinDeformerWeights()
            self.output += sdw.saveWeightInfo(fpath=self.pathLINE.text() + ".skinWeights", meshes=meshSel) + '\n'
            self.refreshUI()
        else:
            cmds.warning('No meshes selected!')
    
    def importFn(self):
        t1 = time.time()
        meshes = [m for m in cmds.ls(type="transform") if isMesh(m)]
        # test if there are meshes in the scene, and rely on name matching rather than having import iterate through a mesh list.
        if meshes:
            #for mesh in meshes:
            fpath = self.pathLINE.text() + '.skinWeights'
            if os.path.isfile(fpath):
                sdw = SkinDeformerWeights(path=fpath)
                sdw.applyWeightInfo()
            else:
                cmds.warning('Cannot find file: ' + fpath)
        
            elapsed = time.time() - t1
            self.output += ('Loaded skinWeights for ' + str(len(meshes)) + ' meshes in ' + str(elapsed) + ' seconds.\n')
            self.refreshUI()
        else:
            cmds.warning('No meshes selected!')

    def setTempPath(self):
        tempDir =  tempfile.gettempdir() + '\\maya_weights\\'
        if not os.path.exists(tempDir):
            os.makedirs(tempDir)
        self.pathLINE.setText(tempDir)
        return tempDir

## DEFORMER WEIGHTS CLASS
class SkinDeformerWeights(object):
    def __init__(self, path=None):
        self.path = path
        self.shapes = {}
        self.fileName = None

        if self.path:
            self.parseFile(self.path)

    class skinnedShape(object):
        def __init__(self, joints=None, shape=None, skin=None, verts=None):
            self.joints = joints
            self.shape = shape
            self.skin = skin
            self.verts = verts

    def applyWeightInfo(self, worldSpace=False, normalize=False, debug=True):
        try:
            #print self.shapes
            for shape in self.shapes:
                #make a skincluster using the joints
                if cmds.objExists(shape):
                    ss = self.shapes[shape]

                    # get joints from XML, confirm joints exist
                    skinList = ss.joints
                    newSkinList = [j for j in skinList if cmds.objExists(j)]
                    for j in newSkinList:
                        if cmds.nodeType(j) != 'joint':
                            print 'NOT A JOINT:', j

                    #Report missing joints
                    for joint in skinList:
                        if joint not in newSkinList:
                            print 'JOINT DOES NOT EXIST:', j

                    newSkinList.append(shape)
                    cmds.select(cl=1)
                    cmds.select(newSkinList)

                    lockedNodes = []

                    for obj in newSkinList:
                        if cmds.lockNode(obj, q=1):
                            if debug:
                                print 'NODE LOCKED:', obj
                            cmds.lockNode(obj, lock=False)
                            lockedNodes.append(obj)

                    # generate new skin cluster
                    cluster = cmds.skinCluster(name=ss.skin, tsb=1, mi=4, sm=0)[0]
                    print '>> skinCluster Influences:', cmds.skinCluster(cluster, inf=1, q=1)
                    fname = self.path.split('\\')[-1]
                    dir = self.path.replace(fname,'')

                    meshVerts = cmds.polyEvaluate(shape, v=1)

                    if ss.verts != meshVerts:
                        cmds.warning('WARNING>>> DeformerWeights>>> VertNum mismatch: file: ' + ss.shape + '[' + str(ss.verts) + '],  ' + shape + ' [' + str(meshVerts) + ']  (Switching to WorldSpace)')
                        worldSpace = True

                    if worldSpace:
                        cmds.deformerWeights(fname, path=dir, deformer=ss.skin, im=1, method='nearest', ws=1)
                        cmds.skinCluster(ss.skin, e=1, forceNormalizeWeights=1)
                    else:
                        # having trouble loading multiple meshes/skin weights. Deformer weights seems to be trying to copy all  the influence 
                        # regardless of what the mesh is actually skinned too. 
                        #cmds.deformerWeights(fname , path = dir, deformer=ss.skin, im=1, method='index')
                        execMe = 'deformerWeights -import -method "index" -deformer \"{0}\" -path \"{1}\" \"{2}\";'.format(ss.skin, dir.replace('\\', '\\\\'), fname)
                        mel.eval(execMe)

                        # This command errors and stops the script execution
                        #cmds.skinCluster(tsb=1, mi=4, sm=0)
                        cmds.skinCluster(ss.skin, e=1, forceNormalizeWeights=1)
                    #drop selection
                    cmds.select(cl=1)

                    if normalize:
                        cmds.skinPercent(cluster, normalize=True)
                    for obj in lockedNodes:
                        cmds.lockNode(obj, lock=True)
                    
        except Exception as e:
            import traceback
            print(traceback.format_exc())

    def saveWeightInfo(self, fpath, meshes, all=True):
        mayaVer = cmds.about(version=True)
        if 'Preview' in mayaVer:
            mayaVer = 2016
        mayaVer = int(mayaVer)
        t1 = time.time()

        #get skin clusters
        meshDict = {}
        for mesh in meshes:
            if isMesh(mesh):
                sc = findRelatedSkinCluster(mesh)
                
                if sc:
                    #remove unused influences
                    removeUnusedInfluences(mesh)
        
                    #not using shape atm, mesh instead
                    msh =  cmds.listRelatives(mesh, shapes=1)
                    meshDict[sc] = mesh
                else:
                    cmds.warning('>>>saveWeightInfo: ' + mesh + ' is not connected to a skinCluster!')
        fname = fpath.split('\\')[-1]
        dir = fpath.replace(fname,'')

        if mayaVer > 2016:
            attributes = ['envelope', 'skinningMethod', 'normalizeWeights', 'deformUserNormals', 'useComponents']
            cmds.deformerWeights(fname, path=dir, ex=1, vc=1, attribute=attributes, deformer=meshDict.keys())
            self.parseFile(fpath)
        else:
            for skin in meshDict:
                cmds.deformerWeights(meshDict[skin] + '.skinWeights', path=dir, ex=1, deformer=skin)
                self.parseFile(fpath + meshDict[skin] + '.skinWeights')

        elapsed = time.time() - t1
        retMe = 'Exported skinWeights for ' + str(len(meshes)) +  ' meshes in ' + str(elapsed) + ' seconds.'
        print retMe
        return retMe

    def parseFile(self, path):
        root = xml.etree.ElementTree.parse(path).getroot()

        self.path = path

        #set the header info
        for atype in root.findall('headerInfo'):
            self.fileName = atype.get('fileName')
        
        # weights is the information for each joint bound to each mesh
        # as a result this is looping through multiple times per mesh. Insteaed 
        for atype in root.findall('weights'):
            jnt = atype.get('source')
            shape = atype.get('shape')
            verts = atype.get('max')
            clusterName = atype.get('deformer')

            if shape not in self.shapes.keys():
                # this is the initial dictionary entry creation, sets the shape, cluster and creates a list with a single joint
                self.shapes[shape] = self.skinnedShape(shape=shape, skin=clusterName, joints=[jnt], verts=None)
            else:
                # if the key is not unique then add the joint to the joint list
                s = self.shapes[shape]
                s.joints.append(jnt)
        
        for atype in root.findall('shape'):
            verts = atype.get('max')
            shape = atype.get("name")

            if verts:
                self.shapes[shape].verts = int(verts)

if __name__ == '__main__':
    show()