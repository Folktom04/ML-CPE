import { render, screen } from '@testing-library/react-native';
import { StyleSheet } from 'react-native';

import { UVCard } from '@/components/UVCard';
import { UvaUvbCard } from '@/components/UvaUvbCard';

import { sampleNight, samplePredict } from './fixtures';

const bg = (id: string) => StyleSheet.flatten(screen.getByTestId(id).props.style).backgroundColor;

describe('UVCard', () => {
  it('shows UVI, range, WHO colour and the q90 warning when the alert level is higher', async () => {
    await render(<UVCard data={samplePredict()} />);
    expect(screen.getByTestId('uvi-value')).toHaveTextContent('5.5');
    expect(screen.getByText('ปานกลาง')).toBeTruthy();
    expect(bg('level-badge')).toBe('#D9A400');
    expect(screen.getByText(/4\.9–6\.7/)).toBeTruthy();
    expect(screen.getByTestId('alert-strip')).toHaveTextContent('เตือนตามค่าบน (q90) 6.7: ระดับสูง');
    expect(bg('alert-strip')).toBe('#E36B12');
    expect(screen.getByTestId('next-safe')).toHaveTextContent('UV กลับสู่ระดับต่ำประมาณ 16:00 น.');
    expect(screen.getByText(/13:00–14:00/)).toBeTruthy();
    expect(screen.queryByTestId('imputed-note')).toBeNull();
  });

  it('hides the warning when both levels match and flags imputed data', async () => {
    await render(
      <UVCard
        data={samplePredict({
          uvi: 9.1,
          level: 'สูงมาก',
          alert_uvi: 10.2,
          alert_level: 'สูงมาก',
          data_imputed: true,
        })}
      />,
    );
    expect(screen.queryByTestId('alert-strip')).toBeNull();
    expect(bg('level-badge')).toBe('#D22F3A');
    expect(screen.getByTestId('imputed-note')).toBeTruthy();
  });

  it('says UV is low now instead of a next-safe time', async () => {
    await render(
      <UVCard data={samplePredict({ uvi: 1.2, level: 'ต่ำ', alert_uvi: 1.6, alert_level: 'ต่ำ' })} />,
    );
    expect(screen.getByTestId('next-safe')).toHaveTextContent('ตอนนี้ UV อยู่ในระดับต่ำ');
    expect(bg('level-badge')).toBe('#3E9B4F');
  });
});

describe('UvaUvbCard', () => {
  it('shows UVA/UVB in W/m², burn minutes for the skin type and the advice', async () => {
    await render(<UvaUvbCard data={samplePredict()} />);
    expect(screen.getByTestId('uva-value')).toHaveTextContent('28.4 W/m²');
    expect(screen.getByTestId('uvb-value')).toHaveTextContent('0.83 W/m²');
    expect(screen.getByText(/ผิวประเภท III/)).toBeTruthy();
    expect(screen.getByTestId('burn-value')).toHaveTextContent('35 นาที');
    expect(screen.getByText('• ทาครีมกันแดด SPF 30+ PA+++')).toBeTruthy();
  });

  it('at night: no burn minutes, no advice, and the next daytime peak instead', async () => {
    const peak = {
      time: '2026-09-28T12:00:00+07:00',
      uvi: 9.6,
      uvi_range: [8.9, 10.4] as [number, number],
      level: 'สูงมาก',
      isTomorrow: true,
    };
    await render(<UvaUvbCard data={sampleNight()} nextPeak={peak} />);
    expect(screen.getByTestId('burn-value')).toHaveTextContent('ไม่มีความเสี่ยง (กลางคืน)');
    expect(screen.queryByText(/แว่นกันแดด/)).toBeNull();
    expect(screen.queryByText(/ออกกลางแจ้งได้ตามปกติ/)).toBeNull();
    const box = screen.getByTestId('next-peak');
    expect(box).toHaveTextContent(/พรุ่งนี้ UV สูงสุดประมาณ/);
    expect(box).toHaveTextContent(/9\.6/);
    expect(box).toHaveTextContent(/ราว 12:00 น\./);
    expect(box).toHaveTextContent(/8\.9–10\.4/);
    expect(bg('next-peak-badge')).toBe('#D22F3A');
  });

  it('at night without a forecast: says so, still no advice', async () => {
    await render(<UvaUvbCard data={sampleNight()} nextPeak={null} />);
    expect(screen.getByTestId('next-peak')).toHaveTextContent('ยังไม่มีข้อมูลพยากรณ์ของวันถัดไป');
    expect(screen.queryByText(/แว่นกันแดด/)).toBeNull();
  });

  it('in daytime the advice is shown and there is no next-peak box', async () => {
    await render(<UvaUvbCard data={samplePredict()} />);
    expect(screen.getByText('• สวมหมวกและแว่นกันแดด')).toBeTruthy();
    expect(screen.queryByTestId('next-peak')).toBeNull();
  });
});
