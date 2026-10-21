# llama-server ni ishga tushiradi: asosiy 7B model + speculative decoding.
# Ishlatish:
#   .\scripts\start_llm.ps1                    # 0.5B draft model bilan (standart)
#   .\scripts\start_llm.ps1 -Spec none         # speculative'siz (solishtirish uchun)
#   .\scripts\start_llm.ps1 -Spec ngram        # draft modelsiz, ngram (matn takrorlanganda tez)
#   .\scripts\start_llm.ps1 -Ctx 12288         # context hajmini o'zgartirish
param(
    [int]$Ctx = 16384,
    [int]$Port = 8080,
    [ValidateSet("draft", "ngram", "none")]
    [string]$Spec = "draft"
)

$LlmHome = if ($env:LLM_HOME) { $env:LLM_HOME } else { "D:\llm" }
$Server  = Join-Path $LlmHome "bin\llama-server.exe"
$Main    = Join-Path $LlmHome "models\qwen2.5-coder-7b-instruct-q4_k_m.gguf"
$Draft   = Join-Path $LlmHome "models\qwen2.5-coder-0.5b-instruct-q8_0.gguf"

$ServerArgs = @(
    "-m", $Main,
    "-ngl", "99",
    "-c", "$Ctx",
    "-fa", "on",
    "-ctk", "q8_0", "-ctv", "q8_0",
    "--port", "$Port",
    "--host", "127.0.0.1"
)
switch ($Spec) {
    "draft" { $ServerArgs += @("--spec-type", "draft-simple", "-md", $Draft, "-ngld", "99", "--spec-draft-n-max", "16", "--spec-draft-n-min", "1") }
    "ngram" { $ServerArgs += @("--spec-type", "ngram-mod") }
}

& $Server @ServerArgs
