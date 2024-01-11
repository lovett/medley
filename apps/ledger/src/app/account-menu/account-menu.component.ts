import { Attribute, Component, Input, OnInit, EventEmitter } from '@angular/core';
import { FormGroup, FormControl } from '@angular/forms';
import { LedgerService } from '../ledger.service';
import { Account } from '../models/account';
import { AccountList } from '../types/accountList';

@Component({
  selector: 'app-account-menu[control]',
  templateUrl: './account-menu.component.html',
  styleUrls: ['./account-menu.component.css'],
})
export class AccountMenuComponent implements OnInit {
    @Input() control!: FormControl;
    @Input() fieldId?: string;
    @Input() label?: string;
    @Input() account?: Account;
    @Input() disabledValue?: string;

    accounts: Account[] = [];

    constructor(
        private ledgerService: LedgerService
    ) {}

    ngOnInit() {
        this.ledgerService.getAccounts().subscribe({
            next: (accountList: AccountList) => {
                for (let primitive of accountList.accounts) {
                    const  a = new Account(primitive);
                    if (a.closed_on && a.uid !== this.control.value) {
                        continue;
                    }
                    this.accounts.push(a);
                }
            },
            error: (err: any) => console.log(err),
        });
    }
}
