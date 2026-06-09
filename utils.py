from decimal import Decimal


def _to_decimal(value: float | int | str | Decimal) -> Decimal:
    return Decimal(str(value))


def compound_interest(rate, years, principal=1):
    r = rate / 100
    total = principal * (1 + r) ** years
    compound_pct = (total / principal - 1) * 100
    return total, compound_pct

# Пример для rate=2.5%, years=4
rate = 10
years = 4
total, compound_pct = compound_interest(rate, years)

print(f"Годовая ставка: {rate}%")
print(f"Период: {years} лет")
print(f"Итоговая сумма: {total:.6f} (от начальной 1)")
print(f"Сложный процент за {years} лет: {compound_pct:.6f}%")
