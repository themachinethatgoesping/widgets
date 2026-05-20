# SPDX-FileCopyrightText: 2022 - 2023 Peter Urban, Ghent University
#
# SPDX-License-Identifier: CC0-1.0

# -- python sources --
sources = [
  'themachinethatgoesping/widgets/__init__.py',
  'themachinethatgoesping/widgets/combinedviewer_core.py',
  'themachinethatgoesping/widgets/combinedviewer_jupyter.py',
  'themachinethatgoesping/widgets/combinedviewer_qt.py',
  'themachinethatgoesping/widgets/control_jupyter.py',
  'themachinethatgoesping/widgets/control_qt.py',
  'themachinethatgoesping/widgets/control_spec.py',
  'themachinethatgoesping/widgets/echogramviewer.py',
  'themachinethatgoesping/widgets/echogramviewer_core.py',
  'themachinethatgoesping/widgets/echogramviewer_jupyter.py',
  'themachinethatgoesping/widgets/echogramviewer_qt.py',
  'themachinethatgoesping/widgets/mapviewer_core.py',
  'themachinethatgoesping/widgets/mapviewer_jupyter.py',
  'themachinethatgoesping/widgets/mapviewer_qt.py',
  'themachinethatgoesping/widgets/pyqtgraph_helpers.py',
  'themachinethatgoesping/widgets/tqdmwidget.py',
  'themachinethatgoesping/widgets/videoframes.py',
  'themachinethatgoesping/widgets/wciviewer.py',
  'themachinethatgoesping/widgets/wciviewer_core.py',
  'themachinethatgoesping/widgets/wciviewer_jupyter.py',
  'themachinethatgoesping/widgets/wciviewer_qt.py',
  'themachinethatgoesping/widgets/tools/__init__.py',
  'themachinethatgoesping/widgets/tools/interactivelinebuilder.py',
]

if get_option('build_pythonmodule').enabled()
    
    if get_option('pydev_install').disabled() #don't install if pydev_install is activated
        foreach source : sources
            #create install path for file
            fields = []
            foreach field : source.split('/')
                if not field.endswith('.py')
                    fields += [field]
                endif
            endforeach
            pth = '/'.join(fields)

            pymod.install_sources(source, subdir: pth, install_tag: 'python-runtime')
        endforeach

    endif
endif
