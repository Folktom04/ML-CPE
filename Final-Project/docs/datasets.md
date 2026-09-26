# Sky-image datasets (sky-CNN module)

The sky CNN is a **separate module**: it classifies the sky condition and estimates cloud fraction
as supporting information in the app. It is trained only on the public datasets below. No photo
taken by the app user is used for training, and the CNN never changes the UVI estimate.
Images are stored in `dataset/sky/` (git-ignored); split tables are in `docs/sky_splits/`.

| Dataset | Content | Licence | Source | Status |
|---|---|---|---|---|
| **CCSN** (Cirrus Cumulus Stratus Nimbus) | 2,543 normal-camera cloud photos, 11 WMO genera (Ac, As, Cb, Cc, Ci, Cs, Ct, Cu, Ns, Sc, St), 256×256 / 400×400 JPEG | **CC0 1.0** | Harvard Dataverse, [doi:10.7910/DVN/CADDPD](https://doi.org/10.7910/DVN/CADDPD), file `CCSN.zip` (md5 `0787f50947a3f65630a7463206316fd3`) | downloaded, verified |
| **SWIMCAT-ext** | 2,100 sky/cloud images, 6 classes × 350 ("All images were collected from Internet and labelled by technical expert", Mendeley description) (clear sky, patterned, thin white, thick white, thick dark, veil), 150×150 PNG | **CC BY 4.0** | Mendeley Data, [doi:10.17632/vwdd9grvdp.1](https://doi.org/10.17632/vwdd9grvdp.1), file `Swimcat-ext.rar` (sha256 `c4f8883c…99fe2d4`) | downloaded, verified |
| SWIMCAT | 784 patches, 5 classes, 125×125 | CC BY-NC 4.0 | [malea.winkler.site/swimcat.html](https://malea.winkler.site/swimcat.html), request form | future work (day 15): not used; cloud fraction uses the red/blue proxy |
| SWIMSEG | 1,013 patches + binary cloud masks, 600×600 | CC BY-NC 4.0 | [malea.winkler.site/swimseg.html](https://malea.winkler.site/swimseg.html), request form | future work (day 15): not used; cloud fraction uses the red/blue proxy |

## Citations
- Zhang, J., Liu, P., Zhang, F., Song, Q. (2018). *CloudNet: Ground-based cloud classification with deep convolutional neural network.* Geophysical Research Letters 45, 8665–8672. Dataset: CCSN Database, Harvard Dataverse, doi:10.7910/DVN/CADDPD.
- Hoang, V. T. (2020). *SWIMCAT-ext* [Dataset]. Mendeley Data, V1, doi:10.17632/vwdd9grvdp.1.
- Dev, S., Lee, Y. H., Winkler, S. (2015). *Categorization of cloud image patches using an improved texton-based approach.* Proc. IEEE ICIP (SWIMCAT).
- Dev, S., Lee, Y. H., Winkler, S. (2017). *Color-based segmentation of sky/cloud images from ground-based cameras.* IEEE J-STARS 10(1), 231–242 (SWIMSEG).

## Licence notes
- CCSN (CC0) and SWIMCAT-ext (CC BY 4.0) allow reuse with attribution. SWIMCAT-ext extends the original SWIMCAT (CC BY-NC 4.0) and its images were collected from the Internet (rights of the original photos are not documented), so we treat it as **non-commercial / educational use only**, as we do SWIMCAT/SWIMSEG. UV Guard is a non-commercial student project.

## Splits (day 13, `src/sky_data.py`)
- Each dataset keeps **its own labels and its own train/val/test split** (70/15/15, stratified, seed 42). There is no merged taxonomy.
- **Near-duplicates** stay in the same split. Two images count as near-duplicates when the mean absolute difference of their 16×16 RGB thumbnails, minimised over the 8 rotations/flips, is < 0.03 (threshold chosen by viewing pairs). dHash alone was tried first and rejected: it chained unrelated low-texture images into groups of ~50 and could not see rotated copies.
- Test splits are readable only with `load_split(..., confirm_test=True)` and are used once on day 14, after the criteria are declared.

## Data-quality findings
- **SWIMCAT-ext:** 1,470 / 2,100 images belong to near-duplicate groups (many images are copies, crops or slight variations of each other; the source does not say how the 2,100 images relate to the 784 SWIMCAT patches). Grouping prevents train/test leakage; the largest group (131) is flat clear-sky patches that look alike.
- **CCSN:** 344 images are in near-duplicate groups; **263 images (124 groups) are the same photo filed under two different genera** (most often Ns/St 20, Cc/Cs 12, Cb/Cu 10, Sc/St 10, Ac/Cc 8). This is label noise inside the published dataset. It is flagged as `label_conflict`; the proposal for day 14 is to drop these groups from every split before training (declared before any model is fit).

- **Cross-dataset (day 15):** the same near-duplicate rule flagged 11 CCSN x SWIMCAT-ext pairs (1 CCSN-train / SWIMCAT-test, 7 train/train, 2 train/val, 1 val/val), but by visual inspection none is the same photo: they are low-texture look-alikes (plain blue sky vs a thin contrail, flat grey veil vs Ac/As/Cc). The 16x16 rule therefore has false positives on flat images. Dropping the one flagged test image changes SWIMCAT-ext test accuracy by less than 0.001 (`docs/sky_cnn_crosscheck.json`).

## Domain gap (limitation)
According to its Mendeley description (doi:10.17632/vwdd9grvdp.1), SWIMCAT-ext is "an extension of SWIMCAT dataset which consists of 2,100 images of sky/cloud patches … All images were collected from Internet and labelled by technical expert." The archive has no further documentation, and the description does not say whether the original SWIMCAT patches (whole-sky imager, Singapore) are included. So SWIMCAT-ext is **not** fisheye sky-camera data (corrected on day 15; earlier notes said so). SWIMSEG, if it arrives, does come from the WAHRSIS whole-sky imager in Singapore. CCSN photos were taken with normal cameras and often include the horizon. App photos are handheld phone shots of the sky. To narrow the gap: centre-crop + resize to 224, then train-time augmentation (flip, ±15° rotation, perspective, brightness, contrast, white balance, saturation, blur). Results on these test splits do not guarantee the same accuracy on phone photos in Pathum Thani.
