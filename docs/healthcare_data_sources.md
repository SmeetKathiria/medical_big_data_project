# Healthcare Data Sources

MedIntel focuses on public healthcare policy, regulatory, and biomedical literature sources: CMS, FDA, and PubMed. It avoids patient-specific diagnosis or treatment framing.

## CMS MCD

CMS Medicare Coverage Database downloads are official ZIP packages. The local small path fetches current Article CSV data and filters for a real CPT/HCPCS code subset. Full archive downloads are handled by `pipeline/jobs/00_download_cms_mcd_archives.py`.

CMS MCD packages may include CPT, CDT, and UB-04 content governed by third-party license terms. Run CMS MCD jobs only after authorization is confirmed by setting `CMS_MCD_LICENSE_ACCEPTED=true` or passing `--cms-license-accepted`.

Supported archive keys:

- `all_data`
- `current_lcd`
- `all_lcd`
- `current_article`
- `all_article`
- `ncd`

Local current archive pull:

```bash
CMS_MCD_LICENSE_ACCEPTED=true make download-cms-mcd-current
```

Full official archive pull, when authorized and when local or remote storage is ready:

```bash
CMS_MCD_LICENSE_ACCEPTED=true make download-cms-mcd-all
```

For larger deployments, keep official archives immutable and process them into the same canonical JSONL layout used locally.
