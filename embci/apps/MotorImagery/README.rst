What is Motor Imagery?
----------------------
A Brain-Computer Interface (BCI) based on Motor Imagery (MI) translates the
subject's motor intention(movement imagination) into a control signal.
Characteristic EEG spatial patterns make MI tasks substantially discriminable.
Algorithms can classify different spatial patterns of EEG which representing
respective intention of movement, like `hand-move-left`, `hand-move-right`,
or `foot-lift` etc.

What is Event-Related Potential?
--------------------------------
As the result of a specific sensory, cognitive, or motor event, the measured
brain signal (aka. EEG) will response according to the event. This kind of EEG
pattern is Event-Related Potential (ERP).

The event can be body movement or just movement intention, real-world stimulus
like temperature or sudden sound, artifact flicker (for P300 and SSVEP) etc.

For example, during a hand movement, the power at Mu(8-12Hz) and Beta(18-26Hz)
rhythms are decreased. This suppression at specific frequency band is known as
Event-Related Desynchronization (ERD).

Brief History of MI
-------------------
- G. Pfurtscheller et al. first used EEG classification based on ERD during
imagined motor actions for a BCI application. Adaptive AutoRegressive (AAR)
was used for feature extraction [1]_.
- Z. Koles etal. first employ CSP in the context of EEG to resolve the
differences in the background EEG [2]_.
- H. Ramoser et al. designed spatial filters by the method of CSP for filtering
single-trial EEG during imagined hand movements [3]_.
- B. Blankerz et al. significantly improved performances of MI-based BCI by
classification on combined feature of ERD and LRP [4]_.
- G. Wentrup et al. implemented multiclass CSP for feature extraction [5]_.

Disadvantages
-------------
- One of the most important factors that prevent MI from real-life application
is that most available algorithms focus on analyzing multi-channel EEG signals.
Which means:
    - multi-channel recording device (EEG-hat, wires and amplifier)
    - tedious preparation and equipments (conductive gel etc)
    - complicated calculation (mostly means PC and long time-delay)

Feature extraction
------------------
Common Spatial Pattern (CSP) is employed to analyze spatial patterns of EEG.
Significant channels are selected by calculating the maximums of spatial
pattern vectors in scalp mappings. After CSP, fewer channels will be selected
according to their spatial pattern vectors because these channels can best
represent the changes of EEG::

    For example, assuming that 128 channels of EEG data are recorded and only
    channel Cz and FCz are most related to the imagine of hand movement, CSP
    can be used to build spatial filters to remove the others 126 useless
    channels.

References
----------
.. [1] G. Pfurtscheller, C. Neuper, A, Schlogl, and K. Lugger. Separability
       of EEG signals recorded during right and left motor imagery using
       adaptive autoregressive parameters. IEEE Trans. Rehab. Eng., vol. 6,
       no. 3, pp.316-325, 1998.
.. [2] Zoltan J. Koles, Michael S. Lazar, Steven Z. Zhou. Spatial Patterns
       Underlying Population Differences in the Background EEG. Brain
       Topography 2(4), 275-284, 1990.
.. [3] H. Ramoser, J. M. Gerking, G. Pfurtscheller. Optimal spatial filtering
       of single trial EEG during imagined hand movement. IEEE Trans. Rehab.
       Eng., vol. 8, no. 4, pp.441-446, 2000.
.. [4] Benjamin Blankertz, Ryota Tomioka, Steven Lemm, Motoaki Kawanabe,
       Klaus-Robert Müller. Optimizing Spatial Filters for Robust EEG
       Single-Trial Analysis. IEEE Signal Processing Magazine 25(1), 41-56,
       2008.
.. [5] Grosse-Wentrup, Moritz, and Martin Buss. Multiclass common spatial
       patterns and information theoretic feature extraction. IEEE
       Transactions on Biomedical Engineering, Vol 55, no. 8, 2008.

See Also
--------
mne.decoding.csp
