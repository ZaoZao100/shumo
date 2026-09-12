param([string]$TaskRoot)
$ErrorActionPreference='Stop'
$docx=Join-Path $TaskRoot 'paper/补齐约束_restrained_v3.docx'
$pdf=Join-Path $TaskRoot 'paper/补齐约束_restrained_v3.pdf'
$word=New-Object -ComObject Word.Application
$word.Visible=$false
$word.DisplayAlerts=0
try {
 $doc=$word.Documents.Open($docx,$false,$true)
 $doc.ExportAsFixedFormat($pdf,17)
 $pages=$doc.ComputeStatistics(2)
 $doc.Close(0)
 "Exported $pages pages" | Set-Content -LiteralPath (Join-Path $TaskRoot 'review/word_export.log') -Encoding utf8
 Write-Output "Exported $pages pages"
} finally {
 $word.Quit()
 [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}

