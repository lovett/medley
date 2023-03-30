import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
    name: 'money'
})
export class MoneyPipe implements PipeTransform {
    numberFormat: Intl.NumberFormat = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
    });

    transform(value: number, style="formatted"): string {
        switch (style) {
            case "plain":
                return (value / 100).toString();
            default:
                return this.numberFormat.format(value/100);
        }
    }
}
