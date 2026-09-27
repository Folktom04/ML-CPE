import { render, screen } from '@testing-library/react-native';
import { StyleSheet } from 'react-native';

import { UVCard } from '@/components/UVCard';
import { UvaUvbCard } from '@/components/UvaUvbCard';

import { samplePredict } from './fixtures';

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

  it('shows no burn minutes at night', async () => {
    await render(
      <UvaUvbCard data={samplePredict({ burn_minutes: null, is_daylight: false, advice: [] })} />,
    );
    expect(screen.getByTestId('burn-value')).toHaveTextContent('ไม่มีความเสี่ยง (กลางคืน)');
  });
});
