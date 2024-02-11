import { Component, OnInit } from '@angular/core';
import { FormGroup, FormBuilder, Validators, AbstractControl, ValidationErrors, AsyncValidatorFn } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { formatDate } from '@angular/common'
import { Account } from '../models/account';
import { LedgerService } from '../ledger.service';
import { Observable, map, of } from 'rxjs';


function dateRange(group: FormGroup): {[key: string]: boolean} | null {
    const openedOn = group.get('opened_on')!.value;
    const closedOn = group.get('closed_on')!.value;

    if (!closedOn) {
        return null;
    }

    if (closedOn >= openedOn) {
        return null;
    }

    return { 'daterange': true }
}

function uniqueName(id: number, ledgerService: LedgerService): AsyncValidatorFn {
    const sanitizer = (value: string) => value.toLowerCase().replace(/\s+/g, '');
    return (control: AbstractControl): Observable<ValidationErrors | null> => {
        if (id !== 0) {
            return of(null);
        }

        const needle = sanitizer(control.value);
        return ledgerService.getAccounts().pipe(
            map(accountList => {
                for (const primitive of accountList.accounts) {
                    if (sanitizer(primitive.name) === needle) {
                        return {'unique': true}
                    }
                }
                return null;
            })
        );
    }
}

@Component({
  selector: 'app-account-form',
  templateUrl: './account-form.component.html',
  styleUrls: ['./account-form.component.css']
})
export class AccountFormComponent implements OnInit {
    accountForm!: FormGroup;
    account: Account | undefined;
    errorMessage = '';
    datesExpanded = false;
    singularResourceName: string;

    constructor(
        private router: Router,
        private route: ActivatedRoute,
        private formBuilder: FormBuilder,
        private ledgerService: LedgerService
    ) {
        this.singularResourceName = 'account';
    }

    ngOnInit(): void {
        const id = Number(this.route.snapshot.paramMap.get('id') || 0)

        this.accountForm = this.formBuilder.group({
            name: [
                null,
                {
                    validators: Validators.required,
                    asyncValidators: uniqueName(id, this.ledgerService),
                    updateOn: 'blur',
                }
            ],
            url: [null],
            dates: this.formBuilder.group({
                opened_on: this.today(),
                closed_on: null,
            }, {validators: dateRange}),
            note: [''],
        });

        this.ledgerService.getAccount(id).subscribe(
            (account: Account) => this.populate(account),
            (err: Error) => console.log(err),
            () => console.log('All done getting account'),
        );
    }

    ngOnDestroy(): void {
    }

    get name() { return this.accountForm.controls['name'] }
    get dates() { return this.accountForm.controls['dates'] as FormGroup }
    get openedOn() { return this.dates.controls['opened_on'] }
    get closedOn() { return this.dates.controls['closed_on'] }
    get note() { return this.accountForm.controls['note'] }
    get url() { return this.accountForm.controls['url'] }

    today() {
        return formatDate(new Date(), 'yyyy-MM-dd', 'en');
    }

    save(): void {
        const a = Account.clone(this.account!);
        a.name = this.name.value;
        a.opened_on = this.openedOn.value || null;
        a.closed_on = this.closedOn.value || null;
        a.note = this.note.value;
        a.url = this.url.value;

        this.ledgerService.saveAccount(a).subscribe({
            next: () => this.saved(),
            error: (err) => this.errorMessage = err,
        });
    }

    saved() {
        this.accountForm.reset();
        this.router.navigate(['/accounts']);
    }

    deleted() {
        this.accountForm.reset();
        this.router.navigate(['/accounts']);
    }

    canDelete(): boolean {
        if (!this.account) {
            return false;
        }
        return this.account.uid > 0;
    }

    reset() {
        if (this.account) {
            this.populate(this.account);
        }
   }

    populate(account: Account) {
        this.accountForm.reset();

        this.accountForm.patchValue({
            name: account.name,
            url: account.url,
            dates: {
                opened_on: account.openedOnYMD(),
                closed_on: account.closedOnYMD(),
            },
            note: account.note,
        });

        this.account = account;
        this.datesExpanded = account.closed_on instanceof Date;
    }

    toggleAccountClosed(event: Event) {
        this.datesExpanded = (event.target as HTMLInputElement).checked;
        this.accountForm.markAsDirty();

        this.dates.patchValue({
            closed_on: (this.datesExpanded)? this.today() : null,
        });
    }

    deleteAccount() {
        if (!this.account) {
            return;
        }

        this.ledgerService.deleteAccount(this.account.uid).subscribe(
            () => this.deleted(),
            (err) => this.errorMessage = err,
        );
    }
}
