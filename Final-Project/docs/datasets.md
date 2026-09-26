# Sky-image datasets (sky-CNN module)

The sky CNN is a **separate module**: it classifies the sky condition and estimates cloud fraction
as supporting information in the app. It is trained only on the public datasets below. No photo
taken by the app user is used for training, and the CNN never changes the UVI estimate.
Images are stored in `dataset/sky/` (git-ignored); split tables are in `docs/sky_splits/`.

| Dataset | Content | Licence | Source | Status |
|---|---|---|---|---|
| **CCSN** (Cirrus Cumulus Stratus Nimbus) | 2,543 normal-camera cloud photos, 11 WMO genera (Ac, As, Cb, Cc, Ci, Cs, Ct, Cu, Ns, Sc, St), 256×256 / 400×400 JPEG | **CC0 1.0** | Harvard Dataverse, [doi:10.7910/DVN/CADDPD](https://doi.org/10.7910/DVN/CADDPD), file `CCSN.zip` (md5 `0787f50947a3f65630a7463206316fd3`) | downloaded, verified |
| **SWIMCAT-ext** | 2,100 sky-camera patches, 6 classes × 350 (clear sky, patterned, thin white, thick white, thick dark, veil), 150×150 PNG | **CC BY 4.0** | Mendeley Data, [doi:10.17632/vwdd9grvdp.1](https://doi.org/10.17632/vwdd9grvdp.1), file `Swimcat-ext.rar` (sha256 `c4f8883c…99fe2d4`) | downloaded, verified |
| SWIMCAT | 784 patches, 5 classes, 125×125 | CC BY-NC 4.0 | [malea.winkler.site/swimcat.html](https://malea.winkler.site/swimcat.html), request form | pending (waiting for the link from the request form) |
| SWIMSEG | 1,013 patches + binary cloud masks, 600×600 | CC BY-NC 4.0 | [malea.winkler.site/swimseg.html](https://malea.winkler.site/swimseg.html), request form | pending (waiting for the link from the request form) |

## Citations
- Zhang, J., Liu, P., Zhang, F., Song, Q. (2018). *CloudNet: Ground-based cloud classification with deep convolutional neural network.* Geophysical Research Letters 45, 8665–8672. Dataset: CCSN Database, Harvard Dataverse, doi:10.7910/DVN/CADDPD.
- Hoang, V. T. (2020). *SWIMCAT-ext* [Dataset]. Mendeley Data, V1, doi:10.17632/vwdd9grvdp.1.
- Dev, S., Lee, Y. H., Winkler, S. (2015). *Categorization of cloud image patches using an improved texton-based approach.* Proc. IEEE ICIP (SWIMCAT).
- Dev, S., Lee, Y. H., Winkler, S. (2017). *Color-based segmentation of sky/cloud images from ground-based cameras.* IEEE J-STARS 10(1), 231–242 (SWIMSEG).

## Licence notes
- CCSN (CC0) and SWIMCAT-ext (CC BY 4.0) allow reuse with attribution. SWIMCAT-ext extends the original SWIMCAT (CC BY-NC 4.0), so we treat it as **non-commercial use only**, as we do SWIMCAT/SWIMSEG. UV Guard is a non-commercial student project.

## Splits (day 13, `src/sky_data.py`)
- Each dataset keeps **its own labels and its own train/val/test split** (70/15/15, stratified, seed 42). There is no merged taxonomy.
- **Near-duplicates** stay in the same split. Two images count as near-duplicates when the mean absolute difference of their 16×16 RGB thumbnails, minimised over the 8 rotations/flips, is < 0.03 (threshold chosen by viewing pairs). dHash alone was tried first and rejected: it chained unrelated low-texture images into groups of ~50 and could not see rotated copies.
- Test splits are readable only with `load_split(..., confirm_test=True)` and are used once on day 14, after the criteria are declared.

## Data-quality findings
- **SWIMCAT-ext:** 1,470 / 2,100 images belong to near-duplicate groups (it was extended from 784 SWIMCAT patches, so many images are copies or slight variations of each other). Grouping prevents train/test leakage; the largest group (131) is flat clear-sky patches that look alike.
- **CCSN:** 344 images are in near-duplicate groups; **263 images (124 groups) are the same photo filed under two different genera** (most often Ns/St 20, Cc/Cs 12, Cb/Cu 10, Sc/St 10, Ac/Cc 8). This is label noise inside the published dataset. It is flagged as `label_conflict`; the proposal for day 14 is to drop these groups from every split before training (declared before any model is fit).

## Domain gap (limitation)
SWIMCAT-ext (and SWIMSEG) come from a ground-based whole-sky imager in Singapore (cropped patches, no horizon). CCSN photos were taken with normal cameras and often include the horizon. App photos are handheld phone shots of the sky. To narrow the gap: centre-crop + resize to 224, then train-time augmentation (flip, ±15° rotation, perspective, brightness, contrast, white balance, saturation, blur). Results on these test splits do not guarantee the same accuracy on phone photos in Pathum Thani.
