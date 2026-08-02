import { describe, expect, it } from 'vitest'
import { formatDisplayDate, formatDatesInText, parseDateString } from './formatDate'

describe('formatDate', () => {
  it('parses ISO dates', () => {
    expect(parseDateString('2020-03-15')).toEqual({ day: 15, month: 3, year: 2020 })
  })

  it('parses DD/MM/YY as day-first', () => {
    expect(parseDateString('04/10/19')).toEqual({ day: 4, month: 10, year: 2019 })
  })

  it('formats English long dates with full year', () => {
    expect(formatDisplayDate('04/10/19', 'en')).toBe('October 4, 2019')
    expect(formatDisplayDate('2020-03-15', 'en')).toBe('March 15, 2020')
  })

  it('formats Spanish long dates with full year', () => {
    expect(formatDisplayDate('04/10/19', 'es')).toBe('4 de octubre de 2019')
  })

  it('formats embedded dates in clinical text', () => {
    const text = 'Visit on 08/04/20 with follow-up 2020-03-15.'
    expect(formatDatesInText(text, 'en')).toBe(
      'Visit on April 8, 2020 with follow-up March 15, 2020.',
    )
  })
})
