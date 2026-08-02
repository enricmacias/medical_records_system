const MONTHS = {
  en: [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ],
  es: [
    'enero',
    'febrero',
    'marzo',
    'abril',
    'mayo',
    'junio',
    'julio',
    'agosto',
    'septiembre',
    'octubre',
    'noviembre',
    'diciembre',
  ],
}

function expandYear(year) {
  if (year >= 100) return year
  return year >= 70 ? 1900 + year : 2000 + year
}

export function parseDateString(value) {
  if (value == null || String(value).trim() === '') return null
  const trimmed = String(value).trim()

  const iso = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (iso) {
    const year = parseInt(iso[1], 10)
    const month = parseInt(iso[2], 10)
    const day = parseInt(iso[3], 10)
    if (month < 1 || month > 12 || day < 1 || day > 31) return null
    return { day, month, year }
  }

  const slash = trimmed.match(/^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})$/)
  if (slash) {
    const a = parseInt(slash[1], 10)
    const b = parseInt(slash[2], 10)
    const year = expandYear(parseInt(slash[3], 10))
    let day
    let month
    if (a > 12) {
      day = a
      month = b
    } else if (b > 12) {
      day = b
      month = a
    } else {
      day = a
      month = b
    }
    if (month < 1 || month > 12 || day < 1 || day > 31) return null
    return { day, month, year }
  }

  return null
}

export function formatDisplayDate(value, locale = 'en') {
  const parsed = parseDateString(value)
  if (!parsed) return value
  const months = MONTHS[locale] ?? MONTHS.en
  const monthName = months[parsed.month - 1]
  if (!monthName) return value
  if (locale === 'es') {
    return `${parsed.day} de ${monthName} de ${parsed.year}`
  }
  return `${monthName} ${parsed.day}, ${parsed.year}`
}

const DATE_IN_TEXT_PATTERN =
  /\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\b/g

export function formatDatesInText(text, locale = 'en') {
  if (!text) return text
  return text.replace(DATE_IN_TEXT_PATTERN, (match) => {
    const formatted = formatDisplayDate(match, locale)
    return formatted ?? match
  })
}
