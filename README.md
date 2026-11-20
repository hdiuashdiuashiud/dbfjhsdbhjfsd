# s

`sklad.json` s velikostmi skladem u každého produktu. Používá ho stránka produktu
(barevná kolečka a tlačítka velikostí), aby nemusela načítat stránky ostatních barev.

- `varianty.json` – přiřazení čísla varianty k velikosti (z exportu variant, aktualizovat jednou za měsíc)
- `sklad.py` – převod feedu
- `.github/workflows/sklad.yml` – automatické spouštění
