; Read-only drawing inspection. No COM, commands, entity edits, or DWG saves.
; ASCII source for compatibility with both legacy and Unicode AutoLISP.
(defun c:MEPREADTEST (/ *error* fh row names lines item path)
  (defun *error* (msg)
    (if fh (close fh))
    (princ (strcat "\nMEPREADTEST error: " msg))
    (princ)
  )
  (setq row (tblnext "LAYER" T))
  (while row
    (setq names (cons (cdr (assoc 2 row)) names))
    (setq row (tblnext "LAYER"))
  )
  (setq names (reverse names))
  (setq lines
    (append
      (list
        "MEP-Manager: read-only drawing inspection"
        (strcat "DWG: " (getvar "DWGPREFIX") (getvar "DWGNAME"))
        (strcat "DWGTITLED: " (itoa (getvar "DWGTITLED")))
        (strcat "Layer count: " (itoa (length names)))
        "Layers (including off/frozen layers):"
      )
      names
      (list "End of report. No DWG changes or saves performed.")
    )
  )
  (foreach item lines (princ (strcat "\n" item)))
  ; Cancel this dialog to keep command-line output only.
  ; Default location is the current DWG folder; choose local_test_data.
  (setq path
    (getfiled
      "Save report in MEP-Manager/local_test_data (Cancel to skip)"
      (strcat (getvar "DWGPREFIX") "MEP-read-report.txt")
      "txt"
      1
    )
  )
  (if path
    (progn
      (setq fh
        (if (= (getvar "LISPSYS") 0)
          (open path "w")
          (open path "w" "utf8-bom")
        )
      )
      (if fh
        (progn
          (foreach item lines (write-line item fh))
          (close fh)
          (setq fh nil)
          (princ (strcat "\nTXT saved: " path))
        )
        (princ "\nCannot open TXT for writing. Report remains in command history.")
      )
    )
    (princ "\nTXT skipped. Report remains in command history.")
  )
  (princ)
)
(princ "\nLoaded. Type MEPREADTEST to read the active DWG path and layers.")
(princ)
